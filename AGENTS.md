# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Project

A reusable GitHub Action that validates Fallout 1/2 modding data files in CI/CD pipelines. The four Python validators are standalone CLI tools; they are orchestrated by `scripts/action.py` when the Action runs.

## Commands

```bash
# Lint (all run in CI)
uv run ruff format --check .
uv run ruff check .
uv run ty check

# Tests
uv run pytest
uv run pytest -m integration  # requires network; clones real Fallout data

# Run a single validator manually
python3 scripts/scripts_lst.py <scripts.h> <scripts.lst>
python3 scripts/lvars.py <scripts_dir> <scripts.lst>
python3 scripts/dialogs.py <dialog_dir> <scripts_dir>
python3 scripts/worldmap.py <worldmap.txt> [-s <set1> <set2> ...]
```

Tests live in `tests/`. Run with `uv run pytest`. Integration tests against real Fallout data require `pytest -m integration` and clone https://github.com/BGforgeNet/Fallout2_Unofficial_Patch into a temp directory.

## Architecture

All source lives in `scripts/`. The four validator modules are independent and do not import from each other; `action.py` imports all four to orchestrate them.

| Module | Input files | What it checks |
|--------|-------------|----------------|
| `scripts_lst.py` | `scripts.h`, `scripts.lst` | Script names match between the C header and the Fallout script list; no duplicates |
| `lvars.py` | `.ssl` files, `scripts.lst` | Allocated local variable count in the list ≥ max LVAR index used in the compiled script source |
| `dialogs.py` | `.msg` files, `.ssl` files | Every message ID referenced in script source exists in the corresponding `.msg` dialog file |
| `worldmap.py` | `worldmap.txt` | Script number combinations in encounter tables belong to a declared allowed set |

**Encoding:** `.msg` dialog files use `cp1252` (Windows-1252). All other files (`scripts.h`, `scripts.lst`, `.ssl` scripts, `worldmap.txt`) are UTF-8/ASCII.

**Exit codes:** 0 = validation passed, 1 = one or more errors found. Errors are printed to stdout.

**Orchestration:** `scripts/action.py` reads `INPUT_*` env vars from `action.yml` and calls each validator's `main()` directly.

## Linter Configuration

Line length is 120. Ruff handles linting (rule sets: `I`, `PL`, `UP`, `B`, `SIM`) and formatting; `ty` handles type checking. Import sorting (`isort`) is enabled with `force-sort-within-sections = true`. All config is in `pyproject.toml`.
