"""Firebase Cloud Functions — License Server API.

Endpoints:
  POST /activate      — Bind a license key to a machine (client)
  POST /validate      — Periodic check-in (client)
  POST /admin_create  — Issue a new license (admin)
  POST /admin_revoke  — Revoke a license (admin)
  POST /admin_release — Release machine binding (admin)
  POST /admin_delete  — Delete a revoked or expired license (admin)
  GET  /admin_list    — List all licenses (admin)
  GET  /admin_status  — Get single license status (admin)
"""
from __future__ import annotations

import json
import os
import secrets as stdlib_secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from firebase_admin import firestore, initialize_app
from firebase_functions import https_fn, options
from firebase_functions.params import SecretParam

# ── Bootstrap ─────────────────────────────────────────────────
initialize_app()

JWT_PRIVATE_KEY = SecretParam("JWT_PRIVATE_KEY")
ADMIN_API_KEY = SecretParam("ADMIN_API_KEY")
MASTER_ADMIN_API_KEY = SecretParam("MASTER_ADMIN_API_KEY")

COLLECTION = "licenses"
REGION = os.environ.get("LICENSE_FUNCTION_REGION", "europe-west1")
MAX_LICENSE_DAYS = 3650
MAX_LICENSE_MACHINES = 25

# Shared error messages
_ERR_POST = "POST required"
_ERR_BAD_JSON = "Invalid JSON body"
_ERR_NOT_FOUND = "License not found"
_ERR_KEY_AND_MID = "license_key and machine_id are required"


def _runtime_options(
    max_instances: int,
    function_secrets: list[SecretParam] | None = None,
) -> dict:
    return {
        "region": REGION,
        "memory": options.MemoryOption.MB_256,
        "max_instances": max_instances,
        "secrets": function_secrets or [],
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return _to_utc_datetime(parsed)
    return None


def _json_default(value: object) -> str:
    if as_dt := _to_utc_datetime(value):
        return as_dt.isoformat()
    return str(value)


def _json_resp(data: dict, status: int = 200) -> https_fn.Response:
    return https_fn.Response(
        json.dumps(data, default=_json_default), status=status,
        headers={"Content-Type": "application/json"},
    )


def _error(msg: str, status: int = 400) -> https_fn.Response:
    return _json_resp({"error": msg}, status)


def _require_post(req: https_fn.Request) -> https_fn.Response | None:
    if req.method != "POST":
        return _error(_ERR_POST, 405)
    return None


def _parse_body(req: https_fn.Request) -> tuple[dict | None, https_fn.Response | None]:
    try:
        body = req.get_json(force=True)
        if isinstance(body, dict) and body:
            return body, None
    except Exception:
        pass
    return None, _error(_ERR_BAD_JSON)


def _body_str(body: dict, key: str) -> str:
    value = body.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def _positive_int(
    body: dict,
    key: str,
    default: int,
    *,
    min_value: int = 1,
    max_value: int | None = None,
) -> tuple[int | None, https_fn.Response | None]:
    raw = body.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, _error(f"{key} must be an integer")
    if value < min_value:
        return None, _error(f"{key} must be at least {min_value}")
    if max_value is not None and value > max_value:
        return None, _error(f"{key} must be at most {max_value}")
    return value, None


def _get_license(key: str) -> tuple[dict | None, https_fn.Response | None]:
    db = firestore.client()
    doc = db.collection(COLLECTION).document(key).get()
    if not doc.exists:
        return None, _error(_ERR_NOT_FOUND, 404)
    return doc.to_dict(), None


def _sign_token(license_key: str, machine_id: str, expires_at: datetime) -> str:
    payload = {"sub": license_key, "mid": machine_id, "exp": expires_at, "iat": _now()}
    return jwt.encode(payload, JWT_PRIVATE_KEY.value, algorithm="RS256")


def _check_active(data: dict) -> https_fn.Response | None:
    if data.get("revoked"):
        return _error("License has been revoked", 403)
    exp = _to_utc_datetime(data.get("expires_at"))
    if exp is None:
        return _error("License expiry is missing or invalid", 500)
    if exp and exp < _now():
        return _error("License has expired", 403)
    return None


def _bind_machine(data: dict, machine_id: str, doc_ref) -> https_fn.Response | None:
    existing = data.get("machine_id")
    machines = list(data.get("machines", []))
    if existing and existing not in machines:
        machines = [existing] + machines
    if machine_id in machines:
        doc_ref.update({"last_validated": _now()})
        return None
    max_machines = data.get("max_machines", 1)
    if not isinstance(max_machines, int):
        max_machines = 1
    if len(machines) >= max_machines:
        return _error(
            f"License already activated on {len(machines)} machine(s). "
            "Contact admin to release a slot.", 409,
        )
    machines.append(machine_id)
    doc_ref.update({
        "machine_id": existing or machine_id, "machines": machines,
        "activated_at": data.get("activated_at") or _now(), "last_validated": _now(),
    })
    return None


def _build_release_update(data: dict, machine_id: str) -> dict:
    if not machine_id:
        return {"machine_id": None, "machines": []}
    machines = [m for m in data.get("machines", []) if m != machine_id]
    update: dict = {"machines": machines}
    if data.get("machine_id") == machine_id:
        update["machine_id"] = machines[0] if machines else None
    return update


# ── Auth ──────────────────────────────────────────────────────
def _is_authorized_admin_token(token: str) -> bool:
    return stdlib_secrets.compare_digest(
        token, ADMIN_API_KEY.value
    ) or stdlib_secrets.compare_digest(token, MASTER_ADMIN_API_KEY.value)


def require_admin(fn):
    @wraps(fn)
    def wrapper(req: https_fn.Request) -> https_fn.Response:
        auth = req.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return _error("Missing Authorization header", 401)
        token = auth[7:]
        if not _is_authorized_admin_token(token):
            return _error("Invalid admin API key", 403)
        return fn(req)
    return wrapper


# ══════════════════════════════════════════════════════════════
# CLIENT ENDPOINTS
# ══════════════════════════════════════════════════════════════

@https_fn.on_request(
    **_runtime_options(max_instances=10, function_secrets=[JWT_PRIVATE_KEY])
)
def activate(req: https_fn.Request) -> https_fn.Response:
    if err := _require_post(req):
        return err
    body, err = _parse_body(req)
    if err:
        return err
    key = _body_str(body, "license_key")
    mid = _body_str(body, "machine_id")
    if not key or not mid:
        return _error(_ERR_KEY_AND_MID)
    data, err = _get_license(key)
    if err:
        return err
    if err := _check_active(data):
        return err
    doc_ref = firestore.client().collection(COLLECTION).document(key)
    if err := _bind_machine(data, mid, doc_ref):
        return err
    exp = _to_utc_datetime(data.get("expires_at"))
    if exp is None:
        return _error("License expiry is missing or invalid", 500)
    return _json_resp({
        "token": _sign_token(key, mid, exp),
        "expires_at": exp.isoformat() if exp else None,
        "customer": data.get("customer", ""),
    })


@https_fn.on_request(
    **_runtime_options(max_instances=10, function_secrets=[JWT_PRIVATE_KEY])
)
def validate(req: https_fn.Request) -> https_fn.Response:
    if err := _require_post(req):
        return err
    body, err = _parse_body(req)
    if err:
        return err
    key = _body_str(body, "license_key")
    mid = _body_str(body, "machine_id")
    if not key or not mid:
        return _error(_ERR_KEY_AND_MID)
    data, err = _get_license(key)
    if err:
        return err
    if data.get("revoked"):
        return _json_resp({"valid": False, "reason": "revoked"}, 403)
    exp = _to_utc_datetime(data.get("expires_at"))
    if exp is None:
        return _json_resp({"valid": False, "reason": "invalid_expiry"}, 500)
    if exp and exp < _now():
        return _json_resp({"valid": False, "reason": "expired"}, 403)
    machines = data.get("machines", [])
    if mid not in machines and mid != data.get("machine_id"):
        return _json_resp({"valid": False, "reason": "machine_mismatch"}, 403)
    firestore.client().collection(COLLECTION).document(key).update({"last_validated": _now()})
    return _json_resp({"valid": True, "token": _sign_token(key, mid, exp)})


# ══════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════

@https_fn.on_request(
    **_runtime_options(
        max_instances=5,
        function_secrets=[ADMIN_API_KEY, MASTER_ADMIN_API_KEY],
    )
)
def admin_create(req: https_fn.Request) -> https_fn.Response:
    if err := _require_post(req):
        return err

    @require_admin
    def handler(r):
        body, err = _parse_body(r)
        if err:
            return err
        customer = _body_str(body, "customer")
        if not customer:
            return _error("customer is required")
        if len(customer) > 200:
            return _error("customer must be 200 characters or fewer")
        days, err = _positive_int(
            body,
            "duration_days",
            365,
            max_value=MAX_LICENSE_DAYS,
        )
        if err:
            return err
        max_m, err = _positive_int(
            body,
            "max_machines",
            1,
            max_value=MAX_LICENSE_MACHINES,
        )
        if err:
            return err
        key = str(uuid.uuid4())
        now = _now()
        exp = now + timedelta(days=days)
        firestore.client().collection(COLLECTION).document(key).set({
            "license_key": key, "customer": customer,
            "created_at": now, "expires_at": exp,
            "activated_at": None, "machine_id": None,
            "machines": [], "last_validated": None,
            "revoked": False, "max_machines": max_m,
        })
        return _json_resp({
            "license_key": key, "customer": customer,
            "expires_at": exp.isoformat(), "max_machines": max_m,
        }, 201)

    return handler(req)


@https_fn.on_request(
    **_runtime_options(
        max_instances=5,
        function_secrets=[ADMIN_API_KEY, MASTER_ADMIN_API_KEY],
    )
)
def admin_revoke(req: https_fn.Request) -> https_fn.Response:
    if err := _require_post(req):
        return err

    @require_admin
    def handler(r):
        body, err = _parse_body(r)
        if err:
            return err
        key = _body_str(body, "license_key")
        if not key:
            return _error("license_key is required")
        _, err = _get_license(key)
        if err:
            return err
        firestore.client().collection(COLLECTION).document(key).update({"revoked": True})
        return _json_resp({"license_key": key, "revoked": True})

    return handler(req)


@https_fn.on_request(
    **_runtime_options(
        max_instances=5,
        function_secrets=[ADMIN_API_KEY, MASTER_ADMIN_API_KEY],
    )
)
def admin_release(req: https_fn.Request) -> https_fn.Response:
    if err := _require_post(req):
        return err

    @require_admin
    def handler(r):
        body, err = _parse_body(r)
        if err:
            return err
        key = _body_str(body, "license_key")
        mid = _body_str(body, "machine_id")
        if not key:
            return _error("license_key is required")
        data, err = _get_license(key)
        if err:
            return err
        update = _build_release_update(data, mid)
        firestore.client().collection(COLLECTION).document(key).update(update)
        return _json_resp({"license_key": key, "machines_remaining": len(update.get("machines", []))})

    return handler(req)


@https_fn.on_request(
    **_runtime_options(
        max_instances=5,
        function_secrets=[ADMIN_API_KEY, MASTER_ADMIN_API_KEY],
    )
)
def admin_delete(req: https_fn.Request) -> https_fn.Response:
    if err := _require_post(req):
        return err

    @require_admin
    def handler(r):
        body, err = _parse_body(r)
        if err:
            return err
        key = _body_str(body, "license_key")
        if not key:
            return _error("license_key is required")
        data, err = _get_license(key)
        if err:
            return err
        revoked = bool(data.get("revoked", False))
        exp = _to_utc_datetime(data.get("expires_at"))
        expired = bool(exp and exp < _now())
        if not (revoked or expired):
            return _error("Only revoked or expired licenses can be deleted", 409)
        firestore.client().collection(COLLECTION).document(key).delete()
        return _json_resp({"license_key": key, "deleted": True})

    return handler(req)


@https_fn.on_request(
    **_runtime_options(
        max_instances=5,
        function_secrets=[ADMIN_API_KEY, MASTER_ADMIN_API_KEY],
    )
)
def admin_list(req: https_fn.Request) -> https_fn.Response:
    if req.method != "GET":
        return _error("GET required", 405)

    @require_admin
    def handler(r):
        docs = firestore.client().collection(COLLECTION).stream()
        items = [{
            "license_key": d.get("license_key"), "customer": d.get("customer"),
            "activated_at": d.get("activated_at"), "expires_at": d.get("expires_at"),
            "machines": d.get("machines", []), "revoked": d.get("revoked", False),
            "max_machines": d.get("max_machines", 1),
            "last_validated": d.get("last_validated"),
        } for doc in docs for d in [doc.to_dict()]]
        return _json_resp({"count": len(items), "licenses": items})

    return handler(req)


@https_fn.on_request(
    **_runtime_options(
        max_instances=5,
        function_secrets=[ADMIN_API_KEY, MASTER_ADMIN_API_KEY],
    )
)
def admin_status(req: https_fn.Request) -> https_fn.Response:
    if req.method != "GET":
        return _error("GET required", 405)

    @require_admin
    def handler(r):
        key = r.headers.get("X-License-Key", "").strip()
        if not key:
            return _error("X-License-Key header required")
        data, err = _get_license(key)
        if err:
            return err
        now = _now()
        exp = _to_utc_datetime(data.get("expires_at"))
        return _json_resp({
            "license_key": data.get("license_key"), "customer": data.get("customer"),
            "created_at": data.get("created_at"), "activated_at": data.get("activated_at"),
            "expires_at": exp, "days_remaining": (exp - now).days if exp else None,
            "machine_id": data.get("machine_id"), "machines": data.get("machines", []),
            "max_machines": data.get("max_machines", 1), "revoked": data.get("revoked", False),
            "last_validated": data.get("last_validated"),
        })

    return handler(req)
