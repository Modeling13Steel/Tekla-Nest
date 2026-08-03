"""LOC budget guard — fails CI when files exceed their per-path budgets.

Run: ``python scripts/check_loc.py``
Exits 0 when all files are within budget, 1 otherwise.

Budgets are defined in `docs/ui-mocks/ROADMAP.md` §10.3 and mirrored here.
Update both this script and the roadmap together when a budget changes.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Budget:
    glob: str
    max_lines: int


# Order matters — first match wins.
BUDGETS: tuple[Budget, ...] = (
    Budget("src/tekla_nest/views/nest_window.py", 320),  # M9 final budget — shell only.
    Budget("src/tekla_nest/views/widgets/*.py", 250),
    Budget("src/tekla_nest/views/*.py", 400),
    Budget("src/tekla_nest/design_system/*.py", 300),
    Budget("src/tekla_nest/services/*.py", 400),
    Budget("src/tekla_nest/theme.py", 350),
)


def count_lines(path: Path) -> int:
    with path.open("rb") as fh:
        return sum(1 for _ in fh)


def main() -> int:
    failures: list[str] = []
    seen: set[Path] = set()
    for budget in BUDGETS:
        for path in sorted(REPO_ROOT.glob(budget.glob)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            lines = count_lines(path)
            if lines > budget.max_lines:
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}: {lines} lines exceeds budget {budget.max_lines}"
                )
    if failures:
        print("LOC budget violations:")
        for msg in failures:
            print(f"  - {msg}")
        return 1
    print("LOC budgets OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
