"""Runtime language catalog for the Qt UI."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from .config.app_config import _BASE_DIR, get_config

LOGGER = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "pt")

_catalog_cache: dict[str, dict[str, Any]] = {}


def languages_dir() -> Path:
    return _BASE_DIR / "resources" / "languages"


def available_languages() -> dict[str, str]:
    return {
        code: str(_catalog(code).get("language", {}).get("name", code))
        for code in SUPPORTED_LANGUAGES
    }


def current_language() -> str:
    code = getattr(get_config(), "language", DEFAULT_LANGUAGE)
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def set_language(code: str) -> str:
    if code not in SUPPORTED_LANGUAGES:
        code = DEFAULT_LANGUAGE
    get_config().language = code
    _catalog(code)
    return code


def tr(key: str, **params: object) -> str:
    value = _lookup(_catalog(current_language()), key)
    if value is None and current_language() != DEFAULT_LANGUAGE:
        value = _lookup(_catalog(DEFAULT_LANGUAGE), key)
    if value is None:
        return key
    text = str(value)
    if params:
        return text.format(**params)
    return text


def tr_error(message: object) -> str:
    """Translate known user-facing error messages while preserving unknown detail."""
    text = str(message or "")
    if not text:
        return ""

    exact_key = _ERROR_EXACT_KEYS.get(text)
    if exact_key:
        return tr(exact_key)

    for pattern, key, fields in _ERROR_PATTERNS:
        match = pattern.search(text)
        if match:
            params = {
                field: match.group(index + 1)
                for index, field in enumerate(fields)
            }
            return tr(key, **params)

    for prefix, key in _ERROR_PREFIX_KEYS:
        if text.startswith(prefix):
            detail = text[len(prefix):].strip()
            if prefix == "License validation failed:":
                reason = detail.split(".", 1)[0].strip()
                return tr(key, reason=_translate_reason(reason))
            return tr(key, detail=tr_error(detail))

    return text


def _catalog(code: str) -> dict[str, Any]:
    if code in _catalog_cache:
        return _catalog_cache[code]
    path = languages_dir() / f"{code}.yaml"
    try:
        import yaml
    except ImportError:
        _catalog_cache[code] = {}
        return _catalog_cache[code]
    if not path.exists():
        _catalog_cache[code] = {}
        return _catalog_cache[code]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        LOGGER.warning("Could not load language catalog '%s': %s", path, exc)
        data = {}
    if not isinstance(data, dict):
        data = {}
    _catalog_cache[code] = data
    return data


def _lookup(catalog: dict[str, Any], key: str) -> object | None:
    value: object = catalog
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _translate_reason(reason: str) -> str:
    key = _ERROR_REASON_KEYS.get(reason)
    return tr(key) if key else reason


_ERROR_EXACT_KEYS = {
    "No part provider configured.": "errors.operations.no_part_provider",
    "No parts loaded.": "errors.operations.no_parts_loaded",
    "No results to report. Run optimization first.": "errors.operations.no_results_report",
    "No results to export. Run optimization first.": "errors.operations.no_results_export",
    "No results to reorder. Run optimization first.": "errors.operations.no_results_reorder",
    "Report profile is no longer available.": "errors.operations.stale_profile",
    "Report bar is no longer available.": "errors.operations.stale_bar",
    "Unsupported report command.": "errors.report.unsupported_command",
    "Unsupported report link.": "errors.report.unsupported_link",
    "Malformed reorder command.": "errors.report.malformed_reorder",
    "Reorder command values must be integers.": "errors.report.reorder_integers",
    "Reorder command target is out of range.": "errors.report.reorder_range",
    "Reorder direction must be up or down.": "errors.report.reorder_direction",
    "Reorder command refers to a stale profile.": "errors.report.stale_profile",
    "Reorder command refers to a stale bar.": "errors.report.stale_bar",
    "License public key is missing.\nRun license-server/scripts/generate_keys.py before building a licensed release, then rebuild the app.": "errors.license.public_key_missing",
    "License public key is empty.\nRegenerate the license keys before building a licensed release.": "errors.license.public_key_empty",
    "License server URL is not configured.\nSet licensing.server_url in config.yaml.": "errors.license.server_url_missing",
    "Cannot reach the license server.\nInternet access is required for first-time activation.": "errors.license.cannot_reach",
    "License server timed out. Try again later.": "errors.license.timeout",
    "License server request failed. Try again later.": "errors.license.request_failed",
    "Activation response did not include a token.": "errors.license.missing_token",
    "Could not create local license storage.": "errors.license.storage_create",
    "Could not save the local license file.": "errors.license.storage_save",
    "No license found.\nPlease activate with your license key.": "errors.license.no_license",
    "License file is corrupted or was copied from another machine.\nPlease re-activate.": "errors.license.corrupted",
    "License was activated on a different machine.\nPlease re-activate on this machine.": "errors.license.different_machine",
    "License has expired.\nContact your administrator to renew.": "errors.license.expired_renew",
    "License token was issued for a different machine.\nPlease re-activate.": "errors.license.token_machine_mismatch",
    "License server returned an invalid response.": "errors.license.invalid_response",
    "License has been revoked": "errors.license.revoked",
    "License has expired": "errors.license.expired",
    "License not found": "errors.license.not_found",
    "license_key and machine_id are required": "errors.license.bad_activation_request",
    "Invalid admin API key": "errors.admin.invalid_key",
    "Missing Authorization header": "errors.admin.missing_auth",
    "License server URL is required": "errors.admin.server_url_required",
    "Admin API key is required": "errors.admin.admin_key_required",
    "customer is required": "errors.admin.customer_required",
    "license_key is required": "errors.admin.license_key_required",
}

_ERROR_PREFIX_KEYS = (
    ("Failed to load parts CSV:", "errors.operations.failed_load_parts_csv"),
    ("Failed to load stock CSV:", "errors.operations.failed_load_stock_csv"),
    ("Failed to load parts:", "errors.operations.failed_load_parts"),
    ("Failed to optimize:", "errors.operations.failed_optimize"),
    ("Failed to generate report:", "errors.operations.failed_report"),
    ("Failed to export PDF:", "errors.operations.failed_export_pdf"),
    ("Failed to export Excel:", "errors.operations.failed_export_excel"),
    ("Failed to export CSV:", "errors.operations.failed_export_csv"),
    ("License validation failed:", "errors.license.validation_failed"),
    ("Invalid license token:", "errors.license.invalid_token"),
    ("Optimizing ", "status.optimizing_profile"),
    ("Server returned a non-JSON response", "errors.admin.non_json"),
    ("Could not reach license server:", "errors.admin.unreachable"),
)

_ERROR_PATTERNS = (
    (
        re.compile(r"^CSV file not found: '([^']+)'", re.MULTILINE),
        "errors.csv.file_not_found",
        ("path",),
    ),
    (
        re.compile(r"^CSV path is not a file: '([^']+)'", re.MULTILINE),
        "errors.csv.not_file",
        ("path",),
    ),
    (
        re.compile(r"^CSV '([^']+)' is not valid UTF-8\.", re.MULTILINE),
        "errors.csv.invalid_utf8",
        ("file",),
    ),
    (
        re.compile(r"^CSV '([^']+)' appears to be empty", re.MULTILINE),
        "errors.csv.empty",
        ("file",),
    ),
    (
        re.compile(r"^CSV '([^']+)' is missing required columns: ([^\n]+)", re.MULTILINE),
        "errors.csv.missing_columns",
        ("file", "columns"),
    ),
    (
        re.compile(r"^Report template not found at '([^']+)'", re.MULTILINE),
        "errors.report.template_missing",
        ("path",),
    ),
    (
        re.compile(r"^Report image not found: (.+)$", re.MULTILINE),
        "errors.report.image_missing",
        ("path",),
    ),
    (
        re.compile(r"^(.+) must be greater than zero\.$", re.MULTILINE),
        "errors.validation.greater_than_zero",
        ("label",),
    ),
    (
        re.compile(r"^(.+) must be an integer\.$", re.MULTILINE),
        "errors.validation.integer",
        ("label",),
    ),
    (
        re.compile(r"^(.+) is already running\.$", re.MULTILINE),
        "errors.operations.already_running",
        ("operation",),
    ),
    (
        re.compile(r"^License already activated on (\d+) machine\(s\)\.", re.MULTILINE),
        "errors.license.machine_limit",
        ("count",),
    ),
)

_ERROR_REASON_KEYS = {
    "revoked": "errors.license.reason_revoked",
    "expired": "errors.license.reason_expired",
    "machine_mismatch": "errors.license.reason_machine_mismatch",
    "invalid_expiry": "errors.license.reason_invalid_expiry",
    "unknown": "errors.license.reason_unknown",
}
