from __future__ import annotations

from datetime import UTC, datetime

import pytest
import requests

from tekla_nest.admin.api_client import AdminApiClient, AdminClientError
from tekla_nest.admin.models import CreateLicenseRequest, LicenseRecord


class _Response:
    def __init__(
        self,
        data: object,
        *,
        ok: bool = True,
        status_code: int = 200,
        text: str = "",
    ) -> None:
        self._data = data
        self.ok = ok
        self.status_code = status_code
        self.text = text

    def json(self) -> object:
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


def test_admin_client_lists_licenses_and_sends_bearer_token(monkeypatch):
    captured: dict[str, object] = {}

    def fake_request(method: str, url: str, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        return _Response({
            "licenses": [
                {
                    "license_key": "key-1",
                    "customer": "Acme",
                    "expires_at": "2030-01-01T00:00:00+00:00",
                    "machines": ["machine-a"],
                    "max_machines": 2,
                    "revoked": False,
                }
            ]
        })

    monkeypatch.setattr(requests, "request", fake_request)

    licenses = AdminApiClient("https://license.example/", "secret").list_licenses()

    assert captured["method"] == "GET"
    assert captured["url"] == "https://license.example/admin_list"
    assert captured["headers"] == {"Authorization": "Bearer secret"}
    assert licenses == [
        LicenseRecord(
            license_key="key-1",
            customer="Acme",
            expires_at=datetime(2030, 1, 1, tzinfo=UTC),
            machines=["machine-a"],
            max_machines=2,
        )
    ]


def test_admin_client_create_uses_expected_payload(monkeypatch):
    captured: dict[str, object] = {}

    def fake_request(method: str, url: str, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return _Response({
            "license_key": "new-key",
            "customer": "Beta",
            "expires_at": "2030-01-01T00:00:00+00:00",
            "max_machines": 3,
        }, status_code=201)

    monkeypatch.setattr(requests, "request", fake_request)

    license_record = AdminApiClient(
        "https://license.example",
        "secret",
    ).create_license(CreateLicenseRequest("Beta", 365, 3))

    assert captured["method"] == "POST"
    assert captured["url"] == "https://license.example/admin_create"
    assert captured["json"] == {
        "customer": "Beta",
        "duration_days": 365,
        "max_machines": 3,
    }
    assert license_record.license_key == "new-key"
    assert license_record.max_machines == 3


def test_admin_client_redacts_key_from_request_errors(monkeypatch):
    def fake_request(*_args, **_kwargs):
        raise requests.RequestException("failed with secret-token")

    monkeypatch.setattr(requests, "request", fake_request)

    with pytest.raises(AdminClientError) as excinfo:
        AdminApiClient("https://license.example", "secret-token").list_licenses()

    message = str(excinfo.value)
    assert "secret-token" not in message
    assert "<redacted>" in message


def test_admin_client_rejects_non_json_response(monkeypatch):
    monkeypatch.setattr(
        requests,
        "request",
        lambda *_args, **_kwargs: _Response(
            ValueError("bad json"),
            ok=False,
            status_code=500,
            text="<html>",
        ),
    )

    with pytest.raises(AdminClientError, match="non-JSON"):
        AdminApiClient("https://license.example", "secret").list_licenses()
