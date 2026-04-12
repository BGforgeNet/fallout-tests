# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A reusable GitHub Action that validates Fallout 1/2 modding data files in CI/CD pipelines. The four Python validators are standalone CLI tools; they are orchestrated by `action.sh` when the Action runs.

## Commands

```bash
# Lint (all run in CI)
uv run ruff format --check .
uv run ruff check .
uv run ty check
shellcheck action.sh init.sh

# Run a single validator manually
python3 scripts/scripts_lst.py <scripts.h> <scripts.lst>
python3 scripts/lvars.py <scripts_dir> <scripts.lst>
python3 scripts/dialogs.py <dialog_dir> <scripts_dir>
python3 scripts/worldmap.py <worldmap.txt> [-s <set1> <set2> ...]
```

There is no test suite — correctness is validated by running the tools against real modding project data.

## Architecture

All source lives in `scripts/`. Each module is an independent validator with its own `main()` entry point; none import from each other.

| Module | Input files | What it checks |
|--------|-------------|----------------|
| `scripts_lst.py` | `scripts.h`, `scripts.lst` | Script names match between the C header and the Fallout script list; no duplicates |
| `lvars.py` | `.ssl` files, `scripts.lst` | Allocated local variable count in the list ≥ max LVAR index used in the compiled script source |
| `dialogs.py` | `.msg` files, `.ssl` files | Every message ID referenced in script source exists in the corresponding `.msg` dialog file |
| `worldmap.py` | `worldmap.txt` | Script number combinations in encounter tables belong to a declared allowed set |

**Encoding:** all Fallout data files are read/written as `cp1252` (Windows-1252).

**Exit codes:** 0 = validation passed, 1 = one or more errors found. Errors are printed to stdout.

**Orchestration:** `action.sh` maps GitHub Action inputs (`INPUT_*` env vars from `action.yml`) to validator invocations. `init.sh` installs a virtualenv for the Action runtime.

## Linter Configuration

Line length is 120. Ruff handles linting (rule sets: `I`, `PL`, `UP`, `B`, `SIM`) and formatting; `ty` handles type checking. Import sorting (`isort`) is enabled with `force-sort-within-sections = true`. All config is in `pyproject.toml`.
