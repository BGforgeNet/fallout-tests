#!/usr/bin/env python3

import argparse
import os
import re
import sys

parser = argparse.ArgumentParser(
    description="Check if there are enough LVARs allowed in scripts.lst",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("SCRIPTS_DIR", help="scripts directory path")
parser.add_argument("SCRIPTS_LST", help="scripts.lst path")
args = parser.parse_args()


def get_lvars_map():
    lvars = {}
    with open(args.SCRIPTS_LST, encoding="cp1252") as fhandle:
        # pylint: disable=invalid-name
        linenum = 0
        for line in fhandle:
            linenum += 1
            match = re.match(r"^(\w+)\.int.*local_vars=(\d+)", line)
            name = match[1].lower()
            num_lvars = int(match[2])
            if name not in lvars:  # scripts.lst uses first entry
                lvars[name] = num_lvars
    return lvars


def get_max_lvar(fpath):
    max_lvar = 0
    found_lvar = False
    with open(fpath, encoding="cp1252") as fhandle:
        for fline in fhandle:
            match = re.match(r"^#define\s+LVAR_\w+\s+\((\d+)\)\s+.*", fline)
            if match:
                found_lvar = True
                cur_lvar = int(match[1])
                max_lvar = max(max_lvar, cur_lvar)

    # LVAR index starts from 0
    if found_lvar:
        max_lvar += 1

    return max_lvar


def main():
    lvars = get_lvars_map()
    found_mismatch = False
    # pylint: disable=unused-variable
    for dir_name, subdir_list, file_list in os.walk(args.SCRIPTS_DIR, topdown=False):
        for file_name in file_list:
            if file_name.endswith(".ssl"):
                path = os.path.join(dir_name, file_name)
                max_lvar = get_max_lvar(path)
                script_name = os.path.splitext(file_name)[0]
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
