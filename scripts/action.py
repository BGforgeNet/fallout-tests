#!/usr/bin/env python3
"""Entry point for the GitHub Action; dispatches to validator scripts based on INPUT_* env vars."""

import os
from pathlib import Path
import sys

import city
import dialogs
import lvars
import maps
import mvars
import quests
import scripts_lst
import worldmap

# action.yml declares worldmap_path as a path that an empty value switches off, but YAML renders an
# unquoted `false` as the string "false", which is truthy in Python and would be read as a filename.
_DISABLED_VALUES = frozenset({"", "false", "no", "off"})


def is_disabled(value: str) -> bool:
    """Return True when an optional path input is switched off rather than pointing at a file."""
    return value.strip().lower() in _DISABLED_VALUES


def parse_script_sets(raw: str) -> list[str]:
    """Convert multiline script sets to CLI format.

    Input: one set per line, numbers separated by spaces or commas, optionally with # or ; comments,
    e.g. "100 101 # note\\n200 201 202 ; note"
    Output: list of comma-separated strings, e.g. ["100,101", "200,201,202"]

    Raises:
        ValueError: a line does not hold exactly one set of script numbers.
    """
    parsed_sets: list[str] = []
    for line in raw.splitlines():
        content = line.split("#", 1)[0].split(";", 1)[0].strip()
        if not content:
            continue
        # Both separators on one line reads as several sets, but a line means exactly one; silently
        # merging them produced an allowlist permitting a combination the author never wrote.
        if "," in content and any(char.isspace() for char in content):
            raise ValueError(f"worldmap_script_sets: {content!r} mixes commas and spaces; put one set per line")
        numbers = content.replace(",", " ").split()
        for number in numbers:
            if not number.isdigit():
                raise ValueError(f"worldmap_script_sets: {number!r} in {content!r} is not a script number")
        parsed_sets.append(",".join(numbers))
    return parsed_sets


def run_quests() -> bool:
    """Run the quests.txt check when INPUT_QUESTS_PATH is set; return whether it failed."""
    quests_path = os.environ.get("INPUT_QUESTS_PATH", "")
    if is_disabled(quests_path):
        return False
    # The engine loads quests.txt and vault13.gam from the same data directory.
    game_msg_dir = Path(os.environ.get("INPUT_GAME_MSG_DIR", "data/text/english/game"))
    return quests.main(
        [
            quests_path,
            "--quests-msg",
            str(game_msg_dir / "quests.msg"),
            "--map-msg",
            str(game_msg_dir / "map.msg"),
            "--gam",
            str(Path(quests_path).parent / "vault13.gam"),
        ]
    )


def run_mvars() -> bool:
    """Run the map variable check when INPUT_MAP_GAM_DIR is set; return whether it failed."""
    map_gam_dir = os.environ.get("INPUT_MAP_GAM_DIR", "")
    if is_disabled(map_gam_dir):
        return False
    return mvars.main([map_gam_dir, os.environ.get("INPUT_SCRIPTS_DIR", "scripts_src")])


def main() -> None:
    """Read INPUT_* env vars and run the appropriate validator scripts.

    Every enabled check runs before the exit code is decided, so one CI run reports every category of
    problem rather than only the first that failed.

    Defaults below must match those declared in action.yml inputs section.
    """
    failed = False

    if os.environ.get("INPUT_CHECK_SCRIPTS", "true") == "true":
        failed |= scripts_lst.main(
            [
                os.environ.get("INPUT_SCRIPTS_H", "scripts_src/headers/scripts.h"),
                os.environ.get("INPUT_SCRIPTS_LST", "data/scripts/scripts.lst"),
            ]
        )

    if os.environ.get("INPUT_CHECK_LVARS", "true") == "true":
        failed |= lvars.main(
            [
                os.environ.get("INPUT_SCRIPTS_DIR", "scripts_src"),
                os.environ.get("INPUT_SCRIPTS_LST", "data/scripts/scripts.lst"),
            ]
        )

    if os.environ.get("INPUT_CHECK_MSGS", "true") == "true":
        failed |= dialogs.main(
            [
                os.environ.get("INPUT_DIALOG_DIR", "data/text/english/dialog"),
                os.environ.get("INPUT_SCRIPTS_DIR", "scripts_src"),
            ]
        )

    maps_path = os.environ.get("INPUT_MAPS_PATH", "")
    maps_enabled = not is_disabled(maps_path)

    city_path = os.environ.get("INPUT_CITY_PATH", "")
    if not is_disabled(city_path):
        # With maps.txt too, entrance map names are resolved against its lookup_name entries; the
        # engine aborts the whole city load when one does not match.
        city_argv = [city_path] + (["--maps", maps_path] if maps_enabled else [])
        failed |= city.main(city_argv)

    if maps_enabled:
        failed |= maps.main([maps_path])

    worldmap_path = os.environ.get("INPUT_WORLDMAP_PATH", "")
    if not is_disabled(worldmap_path):
        worldmap_argv = [worldmap_path]
        scripts_h = os.environ.get("INPUT_SCRIPTS_H", "scripts_src/headers/scripts.h")
        scripts_lst_path = os.environ.get("INPUT_SCRIPTS_LST", "data/scripts/scripts.lst")
        if scripts_h:
            worldmap_argv += ["--scripts-h", scripts_h]
        if scripts_lst_path:
            worldmap_argv += ["--scripts-lst", scripts_lst_path]
        raw_sets = os.environ.get("INPUT_WORLDMAP_SCRIPT_SETS", "")
        try:
            script_sets = parse_script_sets(raw_sets)
        except ValueError as exc:
            # Running with a half-understood allowlist would report combinations the author did permit.
            print(exc)
            failed = True
        else:
            for script_set in script_sets:
                worldmap_argv += ["-s", script_set]
            failed |= worldmap.main(worldmap_argv)

    failed |= run_quests()
    failed |= run_mvars()

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
