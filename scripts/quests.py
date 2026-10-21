#!/usr/bin/env python3
"""Validate quests.txt against the messages and global variables it refers to.

Field layout follows questInit in fallout2-ce src/pipboy.cc: a line not starting with "#" holds five integers
separated by spaces, tabs or commas - location, description, gvar, display threshold, completed threshold -
and a line with fewer is skipped. The Pip-Boy looks the location up in map.msg and the description in
quests.msg, and indexes the global variables with gvar without a bounds check.
quests.txt is UTF-8/ASCII.
"""

import argparse
from pathlib import Path
import re
import sys

import dialogs
import gam

FIELD_COUNT = 5
_DELIMITERS = re.compile(r"[ \t,]+")

parser = argparse.ArgumentParser(
    description="Find quests.txt entries pointing at missing messages or global variables",
)
parser.add_argument("QUESTS_TXT", help="quests.txt path")
parser.add_argument("--quests-msg", dest="quests_msg", required=True, help="game/quests.msg path")
parser.add_argument("--map-msg", dest="map_msg", required=True, help="game/map.msg path")
parser.add_argument("--gam", dest="gam", required=True, help="vault13.gam path")


def parse_fields(line: str) -> list[int] | None:
    """Return the five fields of a quest line, or None for a line the engine skips.

    Args:
        line: One line of quests.txt

    Returns:
        location, description, gvar, display threshold, completed threshold
    """
    if line.lstrip().startswith("#"):
        return None
    tokens = [token for token in _DELIMITERS.split(line.strip()) if token]
    if len(tokens) < FIELD_COUNT:
        return None
    # atoi reads the leading digits and stops; a token without any reads as 0.
    return [int(m[0]) if (m := re.match(r"[+-]?\d+", token)) else 0 for token in tokens[:FIELD_COUNT]]


def find_problems(quests_path: Path, quest_ids: set[str], map_ids: set[str], gvar_count: int) -> list[str]:
    """Check every quest line's message IDs and global variable number.

    Returns:
        One message per problem
    """
    problems = []
    for number, line in enumerate(quests_path.read_text(encoding="utf-8").splitlines(), start=1):
        fields = parse_fields(line)
        if fields is None:
            continue
        location, description, gvar = fields[:3]
        where = f"{quests_path.name} line {number}"
        if str(location) not in map_ids:
            problems.append(f"{where}: location {location} is not in map.msg.")
        if str(description) not in quest_ids:
            problems.append(f"{where}: description {description} is not in quests.msg.")
        if not 0 <= gvar < gvar_count:
            problems.append(f"{where}: gvar {gvar} is outside vault13.gam, which declares {gvar_count}.")
    return problems


def main(argv: list[str] | None = None) -> bool:
    """Main entry point for quests.txt validation.

    Returns:
        True if an input is unreadable or any quest line is broken. The caller owns the exit code.
    """
    args = parser.parse_args(argv)
    for path in (args.QUESTS_TXT, args.quests_msg, args.map_msg, args.gam):
        if not Path(path).is_file():
            print(f"{path} does not exist.")
            return True

    quest_ids = dialogs.get_dialog_messages(args.quests_msg) or []
    map_ids = dialogs.get_dialog_messages(args.map_msg) or []
    gvar_count = gam.count_vars(args.gam, gam.GAME_SECTION)
    if gvar_count is None:
        print(f"{args.gam} has no {gam.GAME_SECTION} section.")
        return True

    problems = find_problems(Path(args.QUESTS_TXT), set(quest_ids), set(map_ids), gvar_count)
    for problem in problems:
        print(problem)
    return bool(problems)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
