#!/usr/bin/env python3
"""Validate map variable numbers against the map .gam files that declare them.

A map's variables come from maps/<map>.gam, counted as gam.py describes, and scripts name them through
MVAR_ defines in headers/<map>.h. The engine rejects an index at or past the count with only a debug
message (mapSetGlobalVar, mapGetGlobalVar in fallout2-ce src/map.cc), so a write is lost and a read
fails. Only used defines are reported: an unused one does nothing at run time.
.gam, .h and .ssl files are UTF-8/ASCII.
"""

import argparse
from pathlib import Path
import re
import sys

import gam
import lvars

_MVAR_DEFINE_RE = re.compile(r"^[ \t]*#define[ \t]+(MVAR_\w+)[ \t]+\((\d+)\)", re.M)
_WORD_RE = re.compile(r"\w+")

parser = argparse.ArgumentParser(
    description="Find map variables that scripts use past the count their map .gam declares",
)
parser.add_argument("MAPS_DIR", help="maps directory holding .gam files")
parser.add_argument("SCRIPTS_DIR", help="scripts directory; map headers are read from its headers/ subdirectory")


def get_users(scripts_dir: Path) -> dict[str, set[str]]:
    """Map each identifier used in a script, outside comments, to the scripts using it."""
    users: dict[str, set[str]] = {}
    for ssl_path in sorted(scripts_dir.rglob("*.ssl")):
        for word in set(_WORD_RE.findall(lvars.strip_comments(ssl_path.read_text(encoding="utf-8")))):
            users.setdefault(word, set()).add(ssl_path.stem)
    return users


def find_problems(maps_dir: Path, scripts_dir: Path) -> list[str]:
    """Report used MVAR defines whose index is not below their map's .gam variable count.

    Returns:
        One message per out-of-range define
    """
    headers = {path.stem.lower(): path for path in (scripts_dir / "headers").glob("*.h")}
    users: dict[str, set[str]] | None = None
    problems = []
    for gam_path in sorted(maps_dir.glob("*.[gG][aA][mM]")):
        header = headers.get(gam_path.stem.lower())
        if header is None:
            continue
        # Without the section marker the engine reads no variables at all.
        count = gam.count_vars(gam_path, gam.MAP_SECTION) or 0
        text = lvars.strip_comments(header.read_text(encoding="utf-8"))
        for name, index in _MVAR_DEFINE_RE.findall(text):
            if int(index) < count:
                continue
            if users is None:
                users = get_users(scripts_dir)
            if name in users:
                problems.append(
                    f"{header.name} defines {name} as {index}, but {gam_path.name} declares {count} map variables; "
                    f"used by {', '.join(sorted(users[name]))}."
                )
    return problems


def main(argv: list[str] | None = None) -> bool:
    """Main entry point for map variable validation.

    Returns:
        True if a directory is missing or a used map variable is out of range. The caller owns the exit code.
    """
    args = parser.parse_args(argv)
    maps_dir = Path(args.MAPS_DIR)
    scripts_dir = Path(args.SCRIPTS_DIR)
    for path in (maps_dir, scripts_dir):
        if not path.is_dir():
            print(f"{path} is not a directory.")
            return True

    problems = find_problems(maps_dir, scripts_dir)
    for problem in problems:
        print(problem)
    return bool(problems)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
