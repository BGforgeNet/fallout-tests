#!/usr/bin/env python3
"""Entry point for the GitHub Action; dispatches to validator scripts based on INPUT_* env vars."""

import os

import dialogs
import lvars
import scripts_lst
import worldmap


def parse_script_sets(raw: str) -> list[str]:
    """Convert multiline script sets to CLI format.

    Input: one space-separated set per line, e.g. "100 101\\n200 201 202"
    Output: list of comma-separated strings, e.g. ["100,101", "200,201,202"]
    """
    return [line.strip().replace(" ", ",") for line in raw.splitlines() if line.strip()]


def main() -> None:
    """Read INPUT_* env vars and run the appropriate validator scripts.

    Defaults below must match those declared in action.yml inputs section.
    """
    if os.environ.get("INPUT_CHECK_SCRIPTS", "true") == "true":
        scripts_lst.main(
            [
                os.environ.get("INPUT_SCRIPTS_H", "scripts_src/headers/scripts.h"),
                os.environ.get("INPUT_SCRIPTS_LST", "data/scripts/scripts.lst"),
            ]
        )

    if os.environ.get("INPUT_CHECK_LVARS", "true") == "true":
        lvars.main(
            [
                os.environ.get("INPUT_SCRIPTS_DIR", "scripts_src"),
                os.environ.get("INPUT_SCRIPTS_LST", "data/scripts/scripts.lst"),
            ]
        )

    if os.environ.get("INPUT_CHECK_MSGS", "true") == "true":
        dialogs.main(
            [
                os.environ.get("INPUT_DIALOG_DIR", "data/text/english/dialog"),
                os.environ.get("INPUT_SCRIPTS_DIR", "scripts_src"),
            ]
        )

    worldmap_path = os.environ.get("INPUT_WORLDMAP_PATH", "")
    if worldmap_path:
        worldmap_argv = [worldmap_path]
        raw_sets = os.environ.get("INPUT_WORLDMAP_SCRIPT_SETS", "")
        if raw_sets:
            worldmap_argv += ["-s", *parse_script_sets(raw_sets)]
        worldmap.main(worldmap_argv)


if __name__ == "__main__":
    main()
