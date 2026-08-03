#!/usr/bin/env python3.12
"""Create the Firebase Python Functions virtual environment.

Firebase CLI source analysis for Python functions expects a `venv` directory
inside the configured functions source directory.
"""
from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path


def main() -> None:
    if sys.version_info[:2] != (3, 12):
        raise SystemExit(
            "Run this script with Python 3.12, for example:\n"
            "  python3.12 scripts/bootstrap_functions_venv.py"
        )

    root = Path(__file__).resolve().parent.parent
    functions_dir = root / "functions"
    venv_dir = functions_dir / "venv"
    requirements = functions_dir / "requirements.txt"

    venv.EnvBuilder(with_pip=True, clear=False).create(venv_dir)
    python = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

    subprocess.run(
        [str(python), "-m", "pip", "install", "--upgrade", "pip"],
        check=True,
    )
    subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(requirements)],
        check=True,
    )
    print(f"Firebase Functions venv ready: {venv_dir}")


if __name__ == "__main__":
    main()
