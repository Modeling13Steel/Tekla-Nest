"""Installer scripts + single-instance mutex stay consistent."""
from __future__ import annotations

import ctypes
import re
import tomllib
from pathlib import Path

import pytest
import yaml

from tekla_nest import single_instance
from tekla_nest.config.app_config import AppConfig

ROOT = Path(__file__).resolve().parents[2]

# AppIds must never change: Inno uses them to find (and upgrade) existing installs.
INSTALLERS = {
    "installer.iss": ("{{B4F2E3A1-7C5D-4E8F-9A2B-1D3C5E7F9A0B}", single_instance.MAIN_APP_MUTEX),
    "installer-admin.iss": ("{{7B0A02A7-47B5-44E6-8D30-4C02B86B26C1}", single_instance.ADMIN_APP_MUTEX),
}


def _setting(text: str, key: str) -> str | None:
    m = re.search(rf"^{key}=(.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


@pytest.mark.parametrize("name", INSTALLERS)
def test_installer_script(name):
    text = (ROOT / name).read_text(encoding="utf-8-sig")
    app_id, mutex = INSTALLERS[name]
    guid = app_id.strip("{}")

    assert not re.search(r'#define\s+MyAppVersion\s+"', text), "version must come from /DMyAppVersion"
    assert _setting(text, "AppVersion") == "{#MyAppVersion}"
    assert _setting(text, "VersionInfoVersion") == "{#MyAppVersion}"
    assert _setting(text, "AppId") == app_id
    assert f"Uninstall\\{{{guid}}}_is1'" in text  # [Code] reads the same app's key
    assert _setting(text, "AppMutex") == mutex
    assert _setting(text, "CloseApplications") == "yes"
    assert _setting(text, "RestartApplications") == "no"
    assert '[InstallDelete]\n' in text
    assert 'Name: "{app}\\_internal"' in text
    assert "function InitializeSetup(): Boolean;" in text
    assert "/ALLOWDOWNGRADE" in text


def test_mutex_names_are_distinct():
    assert single_instance.MAIN_APP_MUTEX != single_instance.ADMIN_APP_MUTEX


def test_default_version_matches_pyproject_and_config_does_not_override():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert AppConfig().version == pyproject["project"]["version"]
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert "version" not in config.get("app", {})


def test_already_running_message_translated():
    for lang in ("en", "pt"):
        data = yaml.safe_load((ROOT / "resources" / "languages" / f"{lang}.yaml").read_text(encoding="utf-8"))
        assert data["dialogs"]["messages"]["app_already_running"]


def test_acquire_is_noop_off_windows(monkeypatch):
    monkeypatch.setattr(single_instance.sys, "platform", "darwin")
    assert single_instance.acquire("x") is True


class _FakeKernel32:
    def __init__(self, handle):
        self.CreateMutexW = lambda *args: (self.calls.append(args), handle)[1]
        self.calls: list = []


@pytest.mark.parametrize(
    ("handle", "last_error", "expected"),
    [(42, 0, True), (42, 183, False), (0, 5, True)],  # first, second instance, fail open
)
def test_acquire_on_windows(monkeypatch, handle, last_error, expected):
    kernel32 = _FakeKernel32(handle)
    monkeypatch.setattr(single_instance.sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "WinDLL", lambda *a, **k: kernel32, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: last_error, raising=False)
    monkeypatch.setattr(single_instance, "_handles", [])

    assert single_instance.acquire("Name") is expected
    assert kernel32.calls == [(None, False, "Name")]
    assert single_instance._handles == ([handle] if handle else [])
