#!/usr/bin/env python3
"""Validate worldmap encounter configurations for Fallout.

This module checks that encounter scripts follow allowed combinations,
preventing invalid script sets from appearing together in encounters.
"""

import argparse
import configparser
import os
import re
import sys
from typing import List, Set

# Type aliases
ScriptSet = List[int]  # A set of script numbers that can appear together
AllowedScriptSets = List[ScriptSet]  # List of allowed script combinations

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

args = parser.parse_args()


def get_allowed_script_sets() -> AllowedScriptSets:
    """Parse command line arguments to extract allowed script sets.

    Returns:
        List of script sets where each set is a list of script numbers
    """
    allowed_script_sets: AllowedScriptSets = []
    if args.script_sets:
        allow_sets = args.script_sets[0]
        for allow_set in allow_sets:
            allow_list = allow_set.split(",")
            # this is for proper sorting
            allow_list = [int(x) for x in allow_list]
            allow_list = sorted(allow_list)
            allowed_script_sets.append(allow_list)
    return allowed_script_sets


def main() -> None:
    """Main entry point for worldmap validation."""
    error = False
    allowed_sets = get_allowed_script_sets()

    if not os.path.exists(args.worldmap):
        print(f"{args.worldmap} does not exist.")
        sys.exit(1)
    if not os.path.isfile(args.worldmap):
        print(f"{args.worldmap} is not a file")
        sys.exit(1)

    wmap = configparser.ConfigParser(interpolation=None)
    wmap.read(args.worldmap)

    for section in wmap.sections():
        if not section.startswith("Encounter: "):
            continue

        options = wmap.options(section)
        scripts: Set[int] = set()
        for option in options:
            value = wmap.get(section, option)

            # Dead critters don't matter.
            if value.startswith("Dead,"):
                continue

            match = re.search(r"Script:(\d+)", value)
            if match:
                script_num = match.groups()[0]
                script_num = int(script_num)
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
