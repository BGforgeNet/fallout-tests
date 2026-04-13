#!/usr/bin/env python3
"""Validate worldmap encounter configurations for Fallout.

This module checks that encounter scripts follow allowed combinations,
preventing invalid script sets from appearing together in encounters.
worldmap.txt is UTF-8/ASCII encoded.
"""

import argparse
import configparser
from pathlib import Path
import re
import sys

# Type aliases
ScriptSet = list[int]  # A set of script numbers that can appear together
AllowedScriptSets = list[ScriptSet]  # List of allowed script combinations

parser = argparse.ArgumentParser(
    description="Find discrepancies in worldmap.txt",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("worldmap", help="worldmap.txt path")
parser.add_argument(
    "-s",
    dest="script_sets",
    help="allow sets of scripts to be present in an encounter together, like so: '-s 100,101  200,201,202'",
    action="append",
    nargs="+",
    required=False,
)


def get_allowed_script_sets(script_sets: list[list[str]] | None) -> AllowedScriptSets:
    """Parse command line script set arguments to extract allowed script sets.

    Args:
        script_sets: Parsed value of the -s argument, or None if not provided

    Returns:
        List of script sets where each set is a list of script numbers
    """
    allowed_script_sets: AllowedScriptSets = []
    if script_sets:
        allow_sets = script_sets[0]
        for allow_set in allow_sets:
            allow_list = allow_set.split(",")
            # Convert to int for proper numeric sorting
            allow_list_int = sorted(int(x) for x in allow_list)
            allowed_script_sets.append(allow_list_int)
    return allowed_script_sets


def main(argv: list[str] | None = None) -> None:
    """Main entry point for worldmap validation."""
    args = parser.parse_args(argv)
    error = False
    allowed_sets = get_allowed_script_sets(args.script_sets)

    worldmap_path = Path(args.worldmap)
    if not worldmap_path.exists():
        print(f"{args.worldmap} does not exist.")
        sys.exit(1)
    if not worldmap_path.is_file():
        print(f"{args.worldmap} is not a file")
        sys.exit(1)

    wmap = configparser.ConfigParser(interpolation=None)
    wmap.read(str(worldmap_path))

    for section in wmap.sections():
        if not section.startswith("Encounter: "):
            continue

        options = wmap.options(section)
        scripts: set[int] = set()
        for option in options:
            value = wmap.get(section, option)

            # Dead critters don't matter.
            if value.startswith("Dead,"):
                continue

            match = re.search(r"Script:(\d+)", value)
            if match:
                script_num = int(match.groups()[0])
                scripts.add(script_num)
        if len(scripts) > 1:
            scripts_list = sorted(scripts)
            if scripts_list not in allowed_sets:
                print(f"{section} has invalid script combination: {scripts_list}")
                error = True
    if error:
        sys.exit(1)


if __name__ == "__main__":
    main()
