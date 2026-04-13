#!/usr/bin/env python3
"""Validate local variable allocations in Fallout scripts.

This module ensures that scripts don't use more local variables (LVARs)
than allocated in scripts.lst, preventing runtime errors.
Only scripts.lst uses cp1252 encoding; .ssl script files are UTF-8/ASCII.
"""

import argparse
from pathlib import Path
import re
import sys

# Type alias for local variable mapping
LVarMap = dict[str, int]  # Maps script name to number of local variables

parser = argparse.ArgumentParser(
    description="Check if there are enough LVARs allowed in scripts.lst",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("SCRIPTS_DIR", help="scripts directory path")
parser.add_argument("SCRIPTS_LST", help="scripts.lst path")


def get_lvars_map(scripts_lst_path: str | Path) -> LVarMap:
    """Parse scripts.lst to extract local variable allocations.

    Args:
        scripts_lst_path: Path to the scripts.lst file

    Returns:
        Dictionary mapping script names to their allocated local variable count
    """
    lvars: LVarMap = {}
    with open(scripts_lst_path, encoding="utf-8") as fhandle:
        for line in fhandle:
            match = re.match(r"^(\w+)\.int.*local_vars=(\d+)", line)
            if match:
                name = match[1].lower()
                num_lvars = int(match[2])
                if name not in lvars:  # scripts.lst uses first entry
                    lvars[name] = num_lvars
    return lvars


def get_max_lvar(fpath: str | Path) -> int:
    """Find the maximum LVAR index used in a script file.

    Args:
        fpath: Path to the script file to analyze

    Returns:
        Maximum number of local variables needed (0 if none found)
    """
    max_lvar: int = 0
    found_lvar: bool = False
    with open(fpath, encoding="utf-8") as fhandle:
        for fline in fhandle:
            match = re.match(r"^#define\s+LVAR_\w+\s+\((\d+)\)\s+.*", fline)
            if match:
                found_lvar = True
                cur_lvar = int(match[1])
                max_lvar = max(max_lvar, cur_lvar)

    # LVAR index starts from 0, so variable count is max index + 1
    if found_lvar:
        max_lvar += 1

    return max_lvar


def main(argv: list[str] | None = None) -> None:
    """Main entry point for LVAR validation."""
    args = parser.parse_args(argv)
    scripts_dir = Path(args.SCRIPTS_DIR)
    scripts_lst_path = Path(args.SCRIPTS_LST)

    lvars = get_lvars_map(scripts_lst_path)
    found_mismatch = False

    for ssl_path in scripts_dir.rglob("*.ssl"):
        max_lvar = get_max_lvar(ssl_path)
        script_name = ssl_path.stem
        if script_name in lvars and lvars[script_name] < max_lvar:
            print(
                f"Script {script_name} max LVAR index is {max_lvar - 1}, "
                f"which requires {max_lvar} variables, "
                f"but scripts.lst only allows {lvars[script_name]}."
            )
            found_mismatch = True

    if found_mismatch:
        sys.exit(1)


if __name__ == "__main__":
    main()
