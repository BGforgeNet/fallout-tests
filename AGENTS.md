# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Project

A reusable GitHub Action that validates Fallout 1/2 modding data files in CI/CD pipelines. The six Python validators are standalone CLI tools; they are orchestrated by `scripts/action.py` when the Action runs.

## Commands

```bash
# Lint (all run in CI)
uv run ruff format --check .
uv run ruff check .
uv run ty check

# Tests
uv run pytest
uv run pytest -m integration  # requires network; uses a managed checkout of real Fallout data
FALLOUT_TEST_REPO=./tmp/Fallout2_Unofficial_Patch uv run pytest -m integration  # choose the cache location

# Run a single validator manually
python3 scripts/scripts_lst.py <scripts.h> <scripts.lst>
python3 scripts/lvars.py <scripts_dir> <scripts.lst>
python3 scripts/dialogs.py <dialog_dir> <scripts_dir>
python3 scripts/city.py <city.txt>
python3 scripts/maps.py <maps.txt>
python3 scripts/worldmap.py <worldmap.txt> [-s <set1> -s <set2> ...]
```

Tests live in `tests/`. Run with `uv run pytest`. Integration tests against real Fallout data require `pytest -m integration` and use a managed checkout of https://github.com/BGforgeNet/Fallout2_Unofficial_Patch pinned by `tests/conftest.py`. If `FALLOUT_TEST_REPO` is set, that path is treated as the managed integration cache and may be updated by the fixture.

CI runs two workflows: `lint.yml` (ruff, ty, the non-integration suite with a coverage gate, and a self-test that invokes `action.yml` against `tests/fixtures/`) and `integration.yml` (the integration suite against the pinned data checkout, cached on the pin). Both gate every push and pull request. The README is consumer-facing only - contributor and test documentation belongs here.

## Architecture

All source lives in `scripts/`. The six validator modules are independent and do not import from each other; `action.py` imports all six to orchestrate them.

Data-file field layouts and value ranges come from the engine source at https://github.com/fallout2-ce/fallout2-ce (`src/worldmap.cc` covers `city.txt`, `maps.txt` and `worldmap.txt`), not from guesswork; cite the function when adding a check.

| Module | Input files | What it checks |
|--------|-------------|----------------|
| `scripts_lst.py` | `scripts.h`, `scripts.lst` | Script names match between the C header and the Fallout script list; no duplicates |
| `lvars.py` | `.ssl` files, `scripts.lst` | Allocated local variable count in the list ≥ max LVAR index used in the compiled script source |
| `dialogs.py` | `.msg` files, `.ssl` files | Every message ID referenced in script source exists in the corresponding `.msg` dialog file |
| `city.py` | `city.txt` | Area definitions: required keys, value ranges, contiguous `Area NN` numbering, and the seven-field entrance layout |
| `maps.py` | `maps.txt` | Map definitions: required keys, value ranges, contiguous `Map NNN` numbering, ambient sfx and start-point lists |
| `worldmap.py` | `worldmap.txt` | Script number combinations in encounter tables belong to a declared allowed set |

**Encoding:** `.msg` dialog files use a legacy codepage and are read as `cp1252` with `errors="replace"`. The English tree is cp1252, but translated trees ship others (cp1250 for Czech and Polish, cp1251 for Russian); only the ASCII `{NNN}` message IDs are extracted, so a lossy decode of the surrounding text cannot change the result. All other files (`scripts.h`, `scripts.lst`, `.ssl` scripts, `worldmap.txt`) are UTF-8/ASCII.

**Language scope:** `dialog_dir` names one tree per invocation and defaults to English. That is deliberate, not an oversight: translations are generated from the PO files under `data/text/po`, so a translated `.msg` legitimately lags its English source, and gating CI on every tree would fail the build on normal translation lag.

**Exit codes:** 0 = validation passed, 1 = one or more errors found. Errors are printed to stdout. Each validator's `main()` returns `True` when it found problems rather than exiting, so `action.py` runs every enabled check and one CI run reports every category instead of stopping at the first failure; the process exit code is set once, at the end.

**Orchestration:** `scripts/action.py` reads `INPUT_*` env vars from `action.yml` and calls each validator's `main()` directly.

## Linter Configuration

Line length is 120. Ruff handles linting (rule sets: `I`, `PL`, `UP`, `B`, `SIM`) and formatting; `ty` handles type checking. Import sorting (`isort`) is enabled with `force-sort-within-sections = true`. All config is in `pyproject.toml`.
