from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import requests


def _load_admin_cli():
    path = Path(__file__).parents[2] / "tekla-iac" / "scripts" / "admin_cli.py"
    spec = importlib.util.spec_from_file_location("license_admin_cli", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Response:
    def __init__(self, data: object, *, ok: bool = True, text: str = "") -> None:
        self._data = data
        self.ok = ok
        self.status_code = 500
        self.text = text

    def json(self) -> object:
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


def test_decode_json_rejects_non_json_response():
    admin_cli = _load_admin_cli()

    with pytest.raises(admin_cli.CliError, match="non-JSON"):
        admin_cli._decode_json(_Response(ValueError("bad"), text="<html>"))


def test_request_sends_bearer_token_and_raises_server_errors(monkeypatch):
    admin_cli = _load_admin_cli()
    monkeypatch.setenv("LICENSE_SERVER_URL", "https://license.example/")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    captured: dict[str, object] = {}

    def fake_request(method: str, url: str, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        return _Response({"error": "Invalid admin API key"}, ok=False)

    monkeypatch.setattr(requests, "request", fake_request)

    with pytest.raises(admin_cli.CliError, match="Invalid admin API key"):
        admin_cli._request("GET", "admin_list")
    assert captured["method"] == "GET"
    assert captured["url"] == "https://license.example/admin_list"
    assert captured["headers"] == {"Authorization": "Bearer secret"}


def test_positive_int_rejects_zero():
    admin_cli = _load_admin_cli()

    with pytest.raises(Exception, match="must be at least 1"):
        admin_cli._positive_int("0")
