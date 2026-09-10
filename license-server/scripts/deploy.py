#!/usr/bin/env python3.12
"""Cross-platform deploy script for the license-server Firebase infrastructure.

Runs, in order (each step is skipped automatically if already satisfied):
  1. Verify/install required CLI tooling (Node.js/npm, firebase-tools, gcloud).
  2. Validate and instantiate cloud credentials (gcloud + firebase login).
  3. One-time project bootstrap (Firestore API/DB, signing keys, functions venv, secrets).
  4. Deploy the Cloud Functions.

Works on macOS, Linux, and Windows. Tool auto-install uses whatever package
manager is already present (brew/apt/dnf/winget/choco); if none is available
you'll get a link and the step is skipped.

Usage:
    python3.12 scripts/deploy.py                 # full flow, prompts before installing/creating things
    python3.12 scripts/deploy.py --yes            # don't prompt (CI-friendly)
    python3.12 scripts/deploy.py --deploy-only    # skip tooling/credential/bootstrap checks
    python3.12 scripts/deploy.py --no-bootstrap   # check tooling/creds but skip one-time bootstrap
    python3.12 scripts/deploy.py --project my-id  # override the project read from .firebaserc
"""
from __future__ import annotations

import argparse
import json
import platform
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # license-server/
KEYS_DIR = ROOT / "keys"
FUNCTIONS_DIR = ROOT / "functions"
VENV_DIR = FUNCTIONS_DIR / "venv"
DEFAULT_FIRESTORE_LOCATION = "eur3"


def run(cmd: list[str], *, check: bool = True, capture: bool = False,
        input_text: str | None = None) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(
        cmd, check=check, cwd=ROOT, text=True, input=input_text, capture_output=capture,
    )


def which(name: str) -> str | None:
    return shutil.which(name)


def confirm(prompt: str, *, default: bool = False, auto_yes: bool = False) -> bool:
    if auto_yes:
        return True
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{prompt} {suffix} ").strip().lower()
    return default if not answer else answer in ("y", "yes")


# --------------------------------------------------------------------------
# Tooling
# --------------------------------------------------------------------------

def ensure_tool(name: str, *, install_hint: str,
                installers: list[tuple[str, list[str]]], auto_yes: bool) -> None:
    """Ensure `name` is on PATH; offer to install via the first available package manager."""
    if which(name):
        print(f"\u2714 {name} found")
        return

    print(f"\u2718 {name} not found on PATH.")
    for manager, cmd in installers:
        if which(manager):
            if confirm(f"Install {name} via `{' '.join(cmd)}`?", default=True, auto_yes=auto_yes):
                run(cmd)
                if which(name):
                    print(f"\u2714 {name} installed")
                    return
                print(f"\u26a0 {name} still not on PATH after install; you may need to restart your shell.")
            break
    raise SystemExit(
        f"{name} is required but not installed and could not be auto-installed.\n{install_hint}"
    )


def ensure_tooling(auto_yes: bool) -> None:
    system = platform.system()  # "Darwin", "Linux", "Windows"

    node_installers: list[tuple[str, list[str]]] = []
    gcloud_installers: list[tuple[str, list[str]]] = []
    if system == "Darwin":
        node_installers.append(("brew", ["brew", "install", "node"]))
        gcloud_installers.append(("brew", ["brew", "install", "--cask", "google-cloud-sdk"]))
    elif system == "Linux":
        node_installers.append(("apt-get", ["sudo", "apt-get", "install", "-y", "nodejs", "npm"]))
        node_installers.append(("dnf", ["sudo", "dnf", "install", "-y", "nodejs", "npm"]))
        gcloud_installers.append(("apt-get", ["sudo", "apt-get", "install", "-y", "google-cloud-cli"]))
    elif system == "Windows":
        node_installers.append(("winget", ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS"]))
        node_installers.append(("choco", ["choco", "install", "nodejs-lts", "-y"]))
        gcloud_installers.append(("winget", ["winget", "install", "-e", "--id", "Google.CloudSDK"]))
        gcloud_installers.append(("choco", ["choco", "install", "gcloudsdk", "-y"]))

    ensure_tool(
        "npm",
        install_hint="Install Node.js (includes npm) from https://nodejs.org/",
        installers=node_installers,
        auto_yes=auto_yes,
    )
    ensure_tool(
        "firebase",
        install_hint="Install manually: npm install -g firebase-tools",
        installers=[("npm", ["npm", "install", "-g", "firebase-tools"])],
        auto_yes=auto_yes,
    )
    ensure_tool(
        "gcloud",
        install_hint="Install manually: https://cloud.google.com/sdk/docs/install",
        installers=gcloud_installers,
        auto_yes=auto_yes,
    )


# --------------------------------------------------------------------------
# Credentials
# --------------------------------------------------------------------------

def ensure_gcloud_auth() -> None:
    result = run(
        ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"],
        capture=True,
    )
    if result.stdout.strip():
        print(f"\u2714 gcloud authenticated as {result.stdout.strip()}")
        return
    print("No active gcloud account. Launching `gcloud auth login`...")
    run(["gcloud", "auth", "login"])


def ensure_firebase_auth() -> None:
    result = run(["firebase", "login:list"], capture=True, check=False)
    if result.returncode == 0 and "No authorized accounts" not in (result.stdout or ""):
        print("\u2714 firebase CLI authenticated")
        return
    print("firebase CLI not authenticated. Launching `firebase login`...")
    run(["firebase", "login"])


def resolve_project_id(explicit: str | None) -> str:
    if explicit:
        run(["firebase", "use", explicit])
        return explicit

    firebaserc = ROOT / ".firebaserc"
    if firebaserc.exists():
        try:
            projects = json.loads(firebaserc.read_text()).get("projects", {})
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Warning: could not read {firebaserc}: {exc}")
            projects = {}
        if projects:
            return next(iter(projects.values()))

    project_id = input("Firebase/GCP project ID: ").strip()
    if not project_id:
        raise SystemExit("A project ID is required.")
    run(["firebase", "use", project_id])
    return project_id


# --------------------------------------------------------------------------
# One-time bootstrap
# --------------------------------------------------------------------------

def secret_exists(name: str, project_id: str) -> bool:
    result = run(
        ["gcloud", "secrets", "describe", name, f"--project={project_id}"],
        capture=True, check=False,
    )
    return result.returncode == 0


def ensure_secret(name: str, project_id: str, *, auto_yes: bool,
                   source_file: Path | None = None, generator=None) -> None:
    if secret_exists(name, project_id):
        print(f"\u2714 Secret {name} already set")
        return
    if not confirm(f"Secret {name} is missing. Create it now?", default=True, auto_yes=auto_yes):
        print(f"\u26a0 Skipping {name} \u2014 deploy will fail until it is set.")
        return
    if source_file is not None:
        run(["firebase", "functions:secrets:set", name], input_text=source_file.read_text())
    else:
        value = generator()
        print(f"{name} = {value}\n(store this in your password vault now \u2014 it will not be shown again)")
        run(["firebase", "functions:secrets:set", name], input_text=value)


def bootstrap_infrastructure(project_id: str, location: str, auto_yes: bool) -> None:
    run(["gcloud", "config", "set", "project", project_id])
    run(["gcloud", "services", "enable", "firestore.googleapis.com", f"--project={project_id}"])

    existing = run(
        ["gcloud", "firestore", "databases", "list", f"--project={project_id}", "--format=value(name)"],
        capture=True, check=False,
    )
    if existing.returncode == 0 and existing.stdout.strip():
        print("\u2714 Firestore database already exists")
    else:
        run([
            "gcloud", "firestore", "databases", "create",
            f"--project={project_id}", "--database=(default)", f"--location={location}",
        ])

    if (KEYS_DIR / "private_key.pem").exists():
        print("\u2714 Signing keys already exist (skipping generation)")
    else:
        run([sys.executable, "scripts/generate_keys.py"])

    if VENV_DIR.exists():
        print("\u2714 Functions venv already exists")
    else:
        run([sys.executable, "scripts/bootstrap_functions_venv.py"])

    ensure_secret("JWT_PRIVATE_KEY", project_id, source_file=KEYS_DIR / "private_key.pem", auto_yes=auto_yes)
    ensure_secret("ADMIN_API_KEY", project_id, generator=lambda: secrets.token_hex(32), auto_yes=auto_yes)
    ensure_secret("MASTER_ADMIN_API_KEY", project_id, generator=lambda: secrets.token_hex(48), auto_yes=auto_yes)


# --------------------------------------------------------------------------
# Deploy
# --------------------------------------------------------------------------

def deploy() -> None:
    if not VENV_DIR.exists():
        run([sys.executable, "scripts/bootstrap_functions_venv.py"])
    run(["firebase", "deploy", "--only", "functions"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", help="Firebase/GCP project ID (default: read from .firebaserc)")
    parser.add_argument("--location", default=DEFAULT_FIRESTORE_LOCATION,
                         help=f"Firestore location for first-time creation (default: {DEFAULT_FIRESTORE_LOCATION})")
    parser.add_argument("--deploy-only", action="store_true",
                         help="Skip tooling/credential/bootstrap checks; just deploy")
    parser.add_argument("--no-bootstrap", action="store_true",
                         help="Skip the one-time infrastructure bootstrap step")
    parser.add_argument("--yes", "-y", action="store_true",
                         help="Don't prompt before installing tools or creating secrets")
    args = parser.parse_args()

    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Run this script with Python 3.12, e.g. `python3.12 scripts/deploy.py`")

    if not args.deploy_only:
        ensure_tooling(args.yes)
        ensure_gcloud_auth()
        ensure_firebase_auth()
        project_id = resolve_project_id(args.project)
        if not args.no_bootstrap:
            bootstrap_infrastructure(project_id, args.location, args.yes)

    deploy()
    print("\n\u2714 Deploy complete.")


if __name__ == "__main__":
    main()
