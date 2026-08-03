from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tekla_nest.config.app_config import load_config, reset_config
from tekla_nest.licensing import license_manager as lm
from tekla_nest.licensing.license_manager import LicenseError, LicenseManager


class _Response:
    def __init__(self, data: object, *, ok: bool = True, text: str = "") -> None:
        self._data = data
        self.ok = ok
        self.text = text

    def json(self) -> object:
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


@pytest.fixture(autouse=True)
def _reset_config():
    reset_config()
    yield
    reset_config()


@pytest.fixture()
def license_env(tmp_path, monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_key = tmp_path / "public_key.pem"
    public_key.write_bytes(public_key_pem)

    token_dir = tmp_path / "licenses"
    monkeypatch.setattr(lm, "_PUBLIC_KEY_FILE", public_key)
    monkeypatch.setattr(lm, "_TOKEN_DIR", token_dir)
    monkeypatch.setattr(lm, "_TOKEN_FILE", token_dir / "license.dat")
    monkeypatch.setattr(lm, "get_machine_id", lambda: "machine-123")

    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "licensing:\n"
        "  required: true\n"
        "  server_url: http://license.test/\n"
        "  revalidation_days: 30\n",
        encoding="utf-8",
    )
    load_config(str(cfg))
    return private_key


def _token(private_key, machine_id: str = "machine-123", license_key: str = "lic-1") -> str:
    return jwt.encode(
        {
            "sub": license_key,
            "mid": machine_id,
            "exp": datetime.now(UTC) + timedelta(days=30),
        },
        private_key,
        algorithm="RS256",
    )


def test_missing_public_key_reports_configuration_error(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "licensing:\n"
        "  required: true\n"
        "  server_url: http://license.test\n",
        encoding="utf-8",
    )
    load_config(str(cfg))
    monkeypatch.setattr(lm, "_PUBLIC_KEY_FILE", tmp_path / "missing.pem")

    with pytest.raises(LicenseError, match="public key is missing"):
        LicenseManager()


def test_activate_saves_token_and_uses_normalized_server_url(
    license_env, monkeypatch
):
    captured: dict[str, object] = {}
    token = _token(license_env)

    def fake_post(url: str, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return _Response({"token": token, "customer": "ACME"})

    monkeypatch.setattr(requests, "post", fake_post)

    manager = LicenseManager()
    result = manager.activate("lic-1")

    assert result["customer"] == "ACME"
    assert captured["url"] == "http://license.test/activate"
    assert captured["json"] == {"license_key": "lic-1", "machine_id": "machine-123"}
    assert manager.is_activated() is True


def test_activate_rejects_non_json_server_response(license_env, monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *_args, **_kwargs: _Response(ValueError("not json"), text="html"),
    )

    with pytest.raises(LicenseError, match="invalid response"):
        LicenseManager().activate("lic-1")


def test_validate_allows_graceful_offline_revalidation(
    license_env, tmp_path, monkeypatch
):
    reset_config()
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "licensing:\n"
        "  required: true\n"
        "  server_url: http://license.test\n"
        "  revalidation_days: 0\n",
        encoding="utf-8",
    )
    load_config(str(cfg))
    manager = LicenseManager()
    manager._save_token("lic-1", _token(license_env))
    monkeypatch.setattr(
        requests,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(requests.ConnectionError()),
    )

    manager.validate()


def test_validate_revoked_response_deactivates_local_license(
    license_env, tmp_path, monkeypatch
):
    reset_config()
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "licensing:\n"
        "  required: true\n"
        "  server_url: http://license.test\n"
        "  revalidation_days: 0\n",
        encoding="utf-8",
    )
    load_config(str(cfg))
    manager = LicenseManager()
    manager._save_token("lic-1", _token(license_env))
    monkeypatch.setattr(
        requests,
        "post",
        lambda *_args, **_kwargs: _Response(
            {"valid": False, "reason": "revoked"},
            ok=False,
        ),
    )

    with pytest.raises(LicenseError, match="revoked"):
        manager.validate()
    assert lm._TOKEN_FILE.exists() is False


def test_corrupt_local_license_file_is_rejected(license_env):
    lm._TOKEN_DIR.mkdir(parents=True)
    lm._TOKEN_FILE.write_text("not-base64", encoding="utf-8")

    with pytest.raises(LicenseError, match="corrupted"):
        LicenseManager().validate()
