"""Reusable HTTP client for Firebase license-admin endpoints."""

from __future__ import annotations

from typing import Any

import requests  # type: ignore[import-untyped]

from .models import CreateLicenseRequest, LicenseRecord


class AdminClientError(RuntimeError):
    """Raised when an admin API request fails."""


class AdminApiClient:
    """Small typed wrapper around the existing Firebase admin endpoints."""

    def __init__(
        self,
        server_url: str,
        admin_key: str,
        *,
        timeout: int = 15,
    ) -> None:
        self.server_url = server_url.strip().rstrip("/")
        self.admin_key = admin_key.strip()
        self.timeout = timeout

    def request(self, method: str, path: str, **kwargs: object) -> dict[str, Any]:
        if not self.server_url:
            raise AdminClientError("License server URL is required")
        if not self.admin_key:
            raise AdminClientError("Admin API key is required")

        try:
            response = requests.request(
                method,
                self._url(path),
                headers=self._headers(),
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise AdminClientError(self._redact(f"Could not reach license server: {exc}")) from exc

        data = decode_json_response(response)
        if not response.ok:
            raise AdminClientError(self._redact(_error_message(data, response.text)))
        return data

    def create_license(self, request: CreateLicenseRequest) -> LicenseRecord:
        data = self.request(
            "POST",
            "admin_create",
            json={
                "customer": request.customer,
                "duration_days": request.duration_days,
                "max_machines": request.max_machines,
            },
        )
        return LicenseRecord.from_api(data)

    def list_licenses(self) -> list[LicenseRecord]:
        data = self.request("GET", "admin_list")
        licenses = data.get("licenses", [])
        if not isinstance(licenses, list):
            raise AdminClientError("Server returned an unexpected license list")
        return [LicenseRecord.from_api(item) for item in licenses if isinstance(item, dict)]

    def status(self, license_key: str) -> LicenseRecord:
        data = self.request("GET", "admin_status", params={"key": license_key})
        return LicenseRecord.from_api(data)

    def revoke(self, license_key: str) -> dict[str, Any]:
        return self.request("POST", "admin_revoke", json={"license_key": license_key})

    def release(
        self,
        license_key: str,
        machine_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {"license_key": license_key}
        if machine_id:
            payload["machine_id"] = machine_id
        return self.request("POST", "admin_release", json=payload)

    def _url(self, path: str) -> str:
        return f"{self.server_url}/{path.strip('/')}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.admin_key}"}

    def _redact(self, text: str) -> str:
        if self.admin_key:
            return text.replace(self.admin_key, "<redacted>")
        return text


def decode_json_response(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise AdminClientError(
            f"Server returned a non-JSON response ({response.status_code}): {response.text[:200]}"
        ) from exc
    if not isinstance(data, dict):
        raise AdminClientError(f"Server returned an unexpected response ({response.status_code})")
    return data


def _error_message(data: dict[str, Any], fallback: str) -> str:
    return str(data.get("error") or data.get("reason") or fallback)
