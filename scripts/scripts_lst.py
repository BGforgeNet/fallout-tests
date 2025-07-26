#!/usr/bin/env python3
"""Validate consistency between scripts.h and scripts.lst files.

This module checks for:
- Duplicate script definitions in scripts.lst
- Mismatched script names between scripts.h and scripts.lst
- Scripts in scripts.lst that are missing from scripts.h
"""

import argparse
import re
import sys
from typing import Dict, Tuple

# Type aliases for clarity
ScriptsByNumber = Dict[int, str]  # Maps script number to script name
ScriptsByName = Dict[str, int]  # Maps script name to script number

parser = argparse.ArgumentParser(
    description="Find discrepancies in scripts.lst and scripts.h",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("SCRIPTS_H", help="scripts.h path")
parser.add_argument("SCRIPTS_LST", help="scripts.lst path")
args = parser.parse_args()


def parse_h() -> Tuple[ScriptsByNumber, ScriptsByName]:
    """Parse scripts.h file to extract script definitions.

    Returns:
        Tuple of (scripts by number, scripts by name) dictionaries
    """
    h_by_num: ScriptsByNumber = {}
    h_by_name: ScriptsByName = {}
    with open(args.SCRIPTS_H, encoding="cp1252") as fhandle:
        for line in fhandle:
            match = re.match(r"^#define\s+SCRIPT_(\w+)\s+\((\d+)\)\s+.*", line)
            if match:
                h_by_num[int(match[2])] = match[1]
                h_by_name[match[1]] = int(match[2])
    return h_by_num, h_by_name


def parse_lst() -> ScriptsByNumber:
    """Parse scripts.lst file to extract script list.

    Returns:
        Dictionary mapping line numbers to script names
    """
    lst_by_num: ScriptsByNumber = {}
    with open(args.SCRIPTS_LST, encoding="cp1252") as fhandle:
        linenum = 0
        for line in fhandle:
            linenum += 1
            scr = line.split(".", maxsplit=1)[0].upper()
            lst_by_num[linenum] = scr
    return lst_by_num


def check_lst_dupes(lst_by_num: ScriptsByNumber) -> bool:
    """Search for duplicate scripts in scripts.lst.

    Args:
        lst_by_num: Dictionary mapping line numbers to script names

    Returns:
        True if duplicates were found, False otherwise
    """
    lst_names = [value for key, value in lst_by_num.items()]
    lst_duped_names = sorted({x for x in lst_names if lst_names.count(x) > 1})
    lst_duped_names = [x for x in lst_duped_names if x != "RESERVED"]

    found_dupes = False
    if len(lst_duped_names) > 0:
        found_dupes = True

    for name in lst_duped_names:
        duped_lines = [key for key, value in lst_by_num.items() if value == name]
        dupes_str = ", ".join([str(x) for x in duped_lines])
        print(f"Dupe: {name} is defined on lines {dupes_str} in scripts.lst")
    return found_dupes


def check_scripts_h(lst_by_num: ScriptsByNumber, h_by_num: ScriptsByNumber, h_by_name: ScriptsByName) -> bool:
    """Search for mismatched names and missing scripts.h defines.

    Args:
        lst_by_num: Scripts from scripts.lst by line number
        h_by_num: Scripts from scripts.h by script number
        h_by_name: Scripts from scripts.h by script name

    Returns:
        True if problems were found, False otherwise
    """
    warning = False
    for i in range(1, len(lst_by_num)):
        if i in h_by_num:
            if lst_by_num[i] != h_by_num[i]:
                print(f"Mismatch: scripts.lst {lst_by_num[i]}, scripts.h {h_by_num[i]}")
                warning = True
        else:
            if (lst_by_num[i] not in h_by_name) and (lst_by_num[i] != "RESERVED"):
                print(f"Missing: script {lst_by_num[i]}.int, line number {i} in scripts.lst is absent from scripts.h")
                warning = True
    return warning


def main() -> None:
    """Main entry point for script validation."""
    h_by_num, h_by_name = parse_h()
    lst_by_num = parse_lst()
    has_lst_dupes = check_lst_dupes(lst_by_num)
    has_scripts_h_problem = check_scripts_h(lst_by_num, h_by_num, h_by_name)

    if has_lst_dupes or has_scripts_h_problem:
        sys.exit(1)


if __name__ == "__main__":
    main()
