# AGENTS.md

Guidance for AI agents working in this repository.

## Project

A reusable GitHub Action that validates Fallout 1/2 modding data in CI. Validators in `scripts/`, each a standalone CLI, orchestrated by `scripts/action.py` reading `INPUT_*` env vars from `action.yml`.

## Commands

```bash
# Lint (all run in CI)
uv run ruff format --check .
uv run ruff check .
uv run ty check

# Tests; integration needs network and a checkout pinned by tests/conftest.py
uv run pytest
uv run pytest -m integration
FALLOUT_TEST_REPO=./tmp/Fallout2_Unofficial_Patch uv run pytest -m integration  # choose the cache location

# Run one validator
python3 scripts/scripts_lst.py <scripts.h> <scripts.lst>
python3 scripts/lvars.py <scripts_dir> <scripts.lst>
python3 scripts/dialogs.py <dialog_dir> <scripts_dir>
python3 scripts/city.py <city.txt> [--maps <maps.txt>]
python3 scripts/maps.py <maps.txt>
python3 scripts/worldmap.py <worldmap.txt> [--scripts-lst <scripts.lst>] [-s <set1> -s <set2> ...]
python3 scripts/quests.py <quests.txt> --quests-msg <quests.msg> --map-msg <map.msg> --gam <vault13.gam>
python3 scripts/mvars.py <maps_dir> <scripts_dir>
```

CI gates every push and PR: `lint.yml` (lint, typecheck, unit suite with a coverage floor, and a self-test invoking `action.yml` against `tests/fixtures/`) and `integration.yml` (integration suite against the cached pinned checkout). The README is consumer-facing; contributor docs belong here.

## Architecture

| Module | Input | What it checks |
|--------|-------|----------------|
| `scripts_lst.py` | `scripts.h`, `scripts.lst` | Names match between header and script list; no duplicates |
| `lvars.py` | `.ssl`, `.h`, `scripts.lst` | Allocated local variable count covers the highest LVAR index used; a script using the `modreact.h` reaction LVARs defines none of its own on their indices 0-3 |
| `dialogs.py` | `.msg`, `.ssl` | Every message ID a script references exists in its `.msg` |
| `city.py` | `city.txt`, optionally `maps.txt` | Required keys, value ranges, contiguous `Area NN`, seven-field entrances; with `--maps`, that each entrance names a declared map |
| `maps.py` | `maps.txt` | Required keys, value ranges, contiguous `Map NNN`, ambient sfx and start-point lists |
| `worldmap.py` | `worldmap.txt`, optionally `scripts.lst` | Encounter script combinations belong to a declared allowed set; table entries name defined encounters; `Script:N` is a `scripts.lst` line |
| `quests.py` | `quests.txt`, `quests.msg`, `map.msg`, `vault13.gam` | Each quest's location and description messages exist and its gvar is declared |
| `mvars.py` | map `.gam`, map headers, `.ssl` | A used `MVAR_` define is below its map's `.gam` variable count |
| `gam.py` | `.gam` | Shared reader: counts variables the way the engine does (not a validator) |

Field layouts and value ranges come from the engine at <https://github.com/fallout2-ce/fallout2-ce> (`src/worldmap.cc` covers `city.txt`, `maps.txt` and `worldmap.txt`) - cite the function when adding a check. Validators may reuse each other where the data spans two files: `city.py` calls `maps.lookup_names()` rather than growing a second reader for that format.

**Exit codes:** 0 = passed, 1 = errors found, printed to stdout. Each `main()` returns whether it found problems instead of exiting, so `action.py` runs every enabled check and one run reports every category; the exit code is set once at the end.

**Encoding:** `.msg` files are read as `cp1252` with `errors="replace"` - translated trees ship other codepages (cp1250 Czech and Polish, cp1251 Russian), and only the ASCII `{NNN}` IDs are extracted, so a lossy decode cannot change the result. Everything else is UTF-8/ASCII.

**Language scope:** `dialog_dir` takes one tree per run, English by default. Deliberate: translations are generated from `data/text/po` and legitimately lag their English source, so gating on every tree would fail CI on normal lag.

## Linting

Line length 120; ruff (`I`, `PL`, `UP`, `B`, `SIM`) for lint and format, `ty` for types. All config lives in `pyproject.toml`.
