# Contributing to Silhouette Card Maker

Thank you for contributing! This document explains the project structure and maintainer workflows so you know which scripts to run when making changes.

## Scripts at a Glance

| Script | Who runs it | Purpose |
|--------|-------------|---------|
| `create_pdf.py` | Users | Generate a print-ready PDF |
| `offset_pdf.py` | Users | Apply printer offset to a PDF |
| `clean_up.py` | Users | Clear `game/front/` and `game/double_sided/` |
| `generate_dxf.py` | Maintainers | Regenerate DXF cutting templates |
| `generate_calibration.py` | Maintainers | Regenerate calibration PDFs |
| `dxf_to_studio3.py` | Maintainers | Convert DXF → `.studio3` (Silhouette Studio) |
| `generate_readme_tables.py` | Maintainers | Regenerate size tables in README |

Internal modules (not run directly): `utilities.py`, `enums.py`, `size_convert.py`, `page_manager.py`, `dxf_manager.py`.

## Development Setup

```sh
python -m venv venv

# macOS/Linux
. venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Adding or Changing Card/Paper Sizes

All card and paper sizes, layouts, and registration mark settings are defined in `assets/layouts.json`. Edit that file first, then regenerate the downstream artifacts in order.

### 1. Edit `assets/layouts.json`

- `paper_sizes`: defines paper dimensions
- `card_sizes`: defines card dimensions
- `layouts`: defines which card/paper combinations exist, their orientation, card grid positions, and registration mark limits

Bump the `version` field on any layout you change — this is used by `dxf_to_studio3.py batch --new` to detect which `.studio3` files need regenerating.

### 2. Regenerate DXF templates

```sh
python generate_dxf.py --all
```

Or for a specific combination:

```sh
python generate_dxf.py --paper_size letter --card_size poker
```

Output goes to `cutting_templates/dxf/`.

### 3. Convert DXF → `.studio3` (requires Silhouette Studio on Windows)

A pre-built calibration file is included at `assets/gui_coordinates.json`, tested on Silhouette Studio 5.0.402ss on Windows with a display scale of 100% and a display resolution of at least 1920×1080. If your setup matches, you can skip to converting templates below.

If the pre-built calibration doesn't work, run a calibration (one-time setup per machine/Studio version):

```sh
python dxf_to_studio3.py calibrate
```

Silhouette Studio will open and you'll be guided through hovering over each UI element and pressing Enter to record its position. Calibration is saved to `assets/gui_coordinates.json`.

Then convert all new/changed templates:

```sh
python dxf_to_studio3.py batch --unit mm --new
```

Or convert everything:

```sh
python dxf_to_studio3.py batch --unit mm
```

Use `--dry_run` to preview what would be converted without launching Silhouette Studio.

Output goes to `cutting_templates/`.

### 4. Regenerate README tables

```sh
python generate_readme_tables.py
```

This updates the card/paper size tables in `README.md`.

### 5. Regenerate calibration PDFs (if paper sizes changed)

```sh
python generate_calibration.py
```

Output goes to `calibration/`.

## Documentation

End-user documentation lives in `README.md` and the per-plugin `plugins/<game>/README.md` files. This fork dropped the local Hugo documentation site to keep the repo lean; the hosted docs at https://alan-cha.github.io/silhouette-card-maker track upstream (Alan-Cha), not this fork.

## Adding a Plugin

See any existing plugin in `plugins/` for the expected structure. Each plugin has:

- `fetch.py` — CLI entry point
- `deck_formats.py` — decklist format parsers
- A game-specific API client

Add a `README.md` in your plugin directory.
