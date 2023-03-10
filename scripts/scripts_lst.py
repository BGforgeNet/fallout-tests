#!/usr/bin/env python3

import sys
import re
import argparse

parser = argparse.ArgumentParser(
    description="Find discrepancies in scripts.lst and scripts.h",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("SCRIPTS_H", help="scripts.h path")
parser.add_argument("SCRIPTS_LST", help="scripts.lst path")
args = parser.parse_args()


def parse_h():
    h_by_num = {}
    h_by_name = {}
    with open(args.SCRIPTS_H, encoding="cp1252") as fhandle:
        for line in fhandle:
            match = re.match(r"^#define\s+SCRIPT_(\w+)\s+\((\d+)\)\s+.*", line)
            if match:
                h_by_num[int(match[2])] = match[1]
                h_by_name[match[1]] = int(match[2])
    return h_by_num, h_by_name


def parse_lst():
    lst_by_num = {}
    with open(args.SCRIPTS_LST, encoding="cp1252") as fhandle:
        linenum = 0
        for line in fhandle:
            linenum += 1
            scr = line.split(".", maxsplit=1)[0].upper()
            lst_by_num[linenum] = scr
    return lst_by_num


def check_lst_dupes(lst_by_num):
    """search dupes in scripts.lst"""
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


def check_scripts_h(lst_by_num, h_by_num, h_by_name) -> bool:
    """search mismatched names and missing scripts.h defines"""
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


def main():
    h_by_num, h_by_name = parse_h()
    lst_by_num = parse_lst()
    has_lst_dupes = check_lst_dupes(lst_by_num)
    has_scripts_h_problem = check_scripts_h(lst_by_num, h_by_num, h_by_name)

    if has_lst_dupes or has_scripts_h_problem:
        sys.exit(1)


if __name__ == "__main__":
    main()
