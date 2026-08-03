session: copilot --resume=e27587bd-474d-49e3-89a8-b81aa477ce0b
# Tekla Nest

1D cutting optimization for steel bar stock.  Reads selected parts from
**Tekla Structures** (or CSV), generates optimal cut plans, and produces
visual HTML/PDF reports.

## Features

- Multi-strategy First Fit Decreasing bin-packing optimizer
- Direct Tekla Structures integration via the Open API (pythonnet)
- CSV import/export for parts and stock
- Auto-generated market stock based on profile family
- Configurable kerf width, scrap threshold, and bar downsizing
- PySide6 GUI with live report preview
- HTML report generation (PDF via optional WeasyPrint)

## Requirements

- Python ≥ 3.9
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Quick start

```bash
# Install dependencies
make install          # or: uv sync

# Run the GUI
make run              # or: uv run tekla-nest

# Run the license admin GUI
make run-admin        # or: uv run tekla-nest-admin

# Run the CLI demo with sample data
make demo             # or: uv run python -m tekla_nest.demo

# Run with your own CSV
make demo CSV=parts.csv
```

## Tekla integration

On Windows with Tekla Structures running, the app automatically detects the
installation and enables the **Import from Tekla** button.  The Tekla bin
folder is resolved in this order:

1. **Environment variable** — `TEKLA_BIN_PATH`, `TEKLA_PATH`, or `TeklaPath`
2. **Windows Registry** — both `SOFTWARE\Tekla\Structures` and
   `SOFTWARE\Trimble\Tekla Structures` (versioned sub-keys, newest first)
3. **Running process** — locates `TeklaStructures.exe` via WMI
4. **Filesystem scan** — common install paths like `C:\TeklaStructures\*`

Tested with Tekla **2021 – 2026**.  Tekla 2026+ moved some assemblies into
a `Net48Runtime/` subfolder; the loader handles both layouts automatically.

To install the Tekla extra:

```bash
uv pip install -e ".[tekla]"
```

If auto-detection fails, set the environment variable manually:

```bash
set TEKLA_BIN_PATH=C:\TeklaStructures\2026.0\bin
```

## Configuration

Edit `config.yaml` to customize branding, stock defaults, kerf width, and
report settings.  See the comments in the file for available options.

## Licensing

Licensed releases use the Firebase-based license server under
`license-server/`. See `license-server/GUIDE.md` for deployment, activation
prompt enablement, admin key management, break-glass recovery, and rotation
procedures.

License administration is available through a separate **Tekla Nest Admin**
desktop app (`tekla-nest-admin`). It is packaged separately from the
customer-facing Tekla Nest app and from the Firebase/license-server
infrastructure package.

## Development

```bash
make install-dev      # Install with dev extras (pytest, pytest-qt)
make test             # Run all tests
make lint             # Lint with ruff
make format           # Auto-format with ruff
make check            # Lint + test
```

## Project structure

```
src/tekla_nest/
├── config/          # YAML configuration loader
├── models/          # Dataclasses (CutPiece, StockBar, BarResult, NestResult)
├── presenters/      # MVP presenter (orchestrates providers ↔ services ↔ views)
├── providers/       # Part sources (Tekla, CSV, manual entry)
├── services/        # Business logic
│   ├── tekla_api.py # Tekla Open API bridge (pythonnet / CLR)
│   ├── nest_engine  # 1D bin-packing optimizer
│   ├── csv_loader   # CSV import / export
│   ├── stock_rules  # Default stock generation
│   └── pdf_report   # HTML / PDF report rendering
└── views/           # PySide6 GUI widgets
```

## Building

```bash
make build            # Wheel + sdist
make binary           # Standalone executable (PyInstaller)
make binary-admin     # Standalone admin executable
make installers       # Separate customer + admin Windows installers
make infrastructure-package  # Separate license-server infrastructure zip
```