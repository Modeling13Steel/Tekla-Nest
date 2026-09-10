#!/usr/bin/env python3
"""Admin CLI for managing licenses.

Usage:
    python scripts/admin_cli.py create --customer "Acme Corp" --days 365
    python scripts/admin_cli.py create --customer "Acme Corp" --days 365 --machines 2
    python scripts/admin_cli.py list
    python scripts/admin_cli.py status --key <uuid>
    python scripts/admin_cli.py revoke --key <uuid>
    python scripts/admin_cli.py release --key <uuid>
    python scripts/admin_cli.py release --key <uuid> --machine <machine_id>

Environment variables:
    LICENSE_SERVER_URL  — base URL (e.g. https://europe-west1-myproj.cloudfunctions.net)
    ADMIN_API_KEY       — admin bearer token; can be set to the break-glass
                          master key only while recovering a lost regular key
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPO_SRC = Path(__file__).resolve().parents[2] / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from tekla_nest.admin.api_client import (  # noqa: E402
    AdminApiClient,
    AdminClientError,
    decode_json_response,
)
from tekla_nest.admin.models import CreateLicenseRequest  # noqa: E402


CliError = AdminClientError


def _env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"Error: {name} environment variable is required", file=sys.stderr)
        sys.exit(1)
    return val


def _url(path: str) -> str:
    base = _env("LICENSE_SERVER_URL").rstrip("/")
    return f"{base}/{path}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {_env('ADMIN_API_KEY')}"}


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _decode_json(resp: object) -> dict:
    return decode_json_response(resp)


def _error_message(data: dict, fallback: str) -> str:
    return str(data.get("error") or data.get("reason") or fallback)


def _request(method: str, path: str, **kwargs) -> dict:
    return AdminApiClient(_env("LICENSE_SERVER_URL"), _env("ADMIN_API_KEY")).request(
        method,
        path,
        **kwargs,
    )


def cmd_create(args: argparse.Namespace) -> None:
    license_record = AdminApiClient(
        _env("LICENSE_SERVER_URL"),
        _env("ADMIN_API_KEY"),
    ).create_license(
        CreateLicenseRequest(
            customer=args.customer,
            duration_days=args.days,
            max_machines=args.machines,
        )
    )
    print(f"License created for: {args.customer}")
    print(f"  Key:     {license_record.license_key}")
    expires = license_record.expires_at.isoformat() if license_record.expires_at else "-"
    print(f"  Expires: {expires}")
    print(f"  Machines: {license_record.max_machines}")


def cmd_list(args: argparse.Namespace) -> None:
    data = _request("GET", "admin_list")
    print(f"Total licenses: {data['count']}\n")
    for lic in data["licenses"]:
        status = "REVOKED" if lic["revoked"] else "ACTIVE"
        machines = len(lic.get("machines", []))
        max_machines = lic.get("max_machines", 1)
        print(f"  [{status}] {lic['license_key']}")
        print(f"    Customer: {lic['customer']}")
        print(f"    Expires:  {lic['expires_at']}")
        print(f"    Machines: {machines}/{max_machines}")
        print()


def cmd_status(args: argparse.Namespace) -> None:
    _print_json(_request("GET", "admin_status", extra_headers={"X-License-Key": args.key}))


def cmd_revoke(args: argparse.Namespace) -> None:
    _request("POST", "admin_revoke", json={"license_key": args.key})
    print(f"License {args.key} revoked.")


def cmd_release(args: argparse.Namespace) -> None:
    payload: dict = {"license_key": args.key}
    if args.machine:
        payload["machine_id"] = args.machine
    data = _request("POST", "admin_release", json=payload)
    print(f"Machine binding released. Remaining: {data.get('machines_remaining', 0)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="License Server Admin CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = sub.add_parser("create", help="Create a new license")
    p_create.add_argument("--customer", required=True, help="Customer name")
    p_create.add_argument("--days", type=_positive_int, default=365, help="Duration in days")
    p_create.add_argument("--machines", type=_positive_int, default=1, help="Max machines")

    # list
    sub.add_parser("list", help="List all licenses")

    # status
    p_status = sub.add_parser("status", help="Get license status")
    p_status.add_argument("--key", required=True, help="License key UUID")

    # revoke
    p_revoke = sub.add_parser("revoke", help="Revoke a license")
    p_revoke.add_argument("--key", required=True, help="License key UUID")

    # release
    p_release = sub.add_parser("release", help="Release machine binding")
    p_release.add_argument("--key", required=True, help="License key UUID")
    p_release.add_argument("--machine", help="Specific machine ID (omit to release all)")

    args = parser.parse_args()
    try:
        {
            "create": cmd_create,
            "list": cmd_list,
            "status": cmd_status,
            "revoke": cmd_revoke,
            "release": cmd_release,
        }[args.command](args)
    except CliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
