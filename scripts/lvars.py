#!/usr/bin/env python3
"""Validate local variable allocations in Fallout scripts.

This module ensures that scripts don't use more local variables (LVARs)
than allocated in scripts.lst, preventing runtime errors, and that a script
using the reaction LVARs reserved by modreact.h keeps their indices free.
scripts.lst, .ssl and .h files are UTF-8/ASCII.
"""

import argparse
from collections.abc import Iterable
from pathlib import Path
import re
import sys

# Type alias for local variable mapping
LVarMap = dict[str, int]  # Maps script name to number of local variables

# modreact.h keeps a critter's reaction in these LVARs, at fixed indices 0-3, and its macros read and write them.
REACTION_LVARS = frozenset({"LVAR_reaction", "LVAR_reaction_level", "LVAR_got_reaction", "LVAR_base_reaction"})
REACTION_INDICES = range(4)

# Strings are matched first so that comment markers inside them are kept.
_COMMENT_RE = re.compile(r'("(?:[^"\\\n]|\\.)*")|//[^\n]*|/\*.*?\*/', re.S)
_DEFINE_RE = re.compile(r"^[ \t]*#[ \t]*define[ \t]+(\w+)(.*)$", re.M)
_PROCEDURE_RE = re.compile(r"^[ \t]*procedure[ \t]+(\w+)[^;\n]*\bbegin\b(.*?)^end\b", re.M | re.S | re.I)
_INCLUDE_SSL_RE = re.compile(r'^[ \t]*#[ \t]*include[ \t]+"([^"]+\.ssl)"', re.M | re.I)
_LVAR_DEFINE_RE = re.compile(r"^[ \t]*#define[ \t]+(LVAR_\w+)[ \t]+\((\d+)\)", re.M)
_WORD_RE = re.compile(r"\w+")

parser = argparse.ArgumentParser(
    description="Check if there are enough LVARs allowed in scripts.lst, and that reaction LVAR indices stay free",
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


def strip_comments(text: str) -> str:
    """Remove // and /* */ comments, keeping string literals and the line count."""
    return _COMMENT_RE.sub(lambda m: m[1] or "\n" * m[0].count("\n") or " ", text)


def get_reaction_names(header_paths: Iterable[Path]) -> frozenset[str]:
    """Find the names whose expansion touches the reaction LVARs.

    Starts from the reaction LVARs and adds every header macro or procedure whose body uses a name already found,
    until nothing new turns up, so a macro that calls a reaction macro counts too.

    Args:
        header_paths: Header files to read macro and procedure definitions from

    Returns:
        The reaction LVARs and every macro or procedure that reaches them
    """
    bodies: dict[str, set[str]] = {}
    for path in header_paths:
        text = re.sub(r"\\\r?\n", " ", strip_comments(path.read_text(encoding="utf-8")))
        for regex in (_DEFINE_RE, _PROCEDURE_RE):
            for name, body in regex.findall(text):
                bodies.setdefault(name, set()).update(_WORD_RE.findall(body))

    names = set(REACTION_LVARS)
    changed = True
    while changed:
        changed = False
        for name, words in bodies.items():
            if name not in names and not words.isdisjoint(names):
                names.add(name)
                changed = True
    return frozenset(names)


def read_with_includes(ssl_path: Path, seen: set[Path] | None = None) -> str:
    """Read a script without comments, followed by the .ssl files it includes, recursively.

    Args:
        ssl_path: Script to read
        seen: Files already read, so an include cycle stops

    Returns:
        The comment-free text of the script and its included scripts
    """
    seen = set() if seen is None else seen
    seen.add(ssl_path.resolve())
    text = strip_comments(ssl_path.read_text(encoding="utf-8"))
    parts = [text]
    for include in _INCLUDE_SSL_RE.findall(text):
        path = (ssl_path.parent / include).resolve()
        # A missing include fails the build itself; here it only narrows what is scanned.
        if path.is_file() and path not in seen:
            parts.append(read_with_includes(path, seen))
    return "\n".join(parts)


def get_reaction_clashes(script_text: str, reaction_names: frozenset[str]) -> list[tuple[str, int]]:
    """List the script's own LVARs on the reaction indices, if the script uses the reaction LVARs.

    Args:
        script_text: Comment-free script text, as read_with_includes returns it
        reaction_names: Names that reach the reaction LVARs, from get_reaction_names

    Returns:
        (name, index) of each clashing LVAR define; empty when the script does not use the reaction LVARs
    """
    clashes = [
        (name, int(index))
        for name, index in _LVAR_DEFINE_RE.findall(script_text)
        if int(index) in REACTION_INDICES and name not in REACTION_LVARS
    ]
    if clashes and reaction_names.isdisjoint(_WORD_RE.findall(script_text)):
        return []
    return clashes


def main(argv: list[str] | None = None) -> bool:
    """Main entry point for LVAR validation.

    Returns:
        True if any script needs more local variables than scripts.lst allows, or defines its own LVAR on an index
        that the reaction LVARs it uses occupy. The caller owns the exit code.
    """
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

    reaction_names = get_reaction_names(scripts_dir.rglob("*.h"))
    for ssl_path in sorted(scripts_dir.rglob("*.ssl")):
        for name, index in get_reaction_clashes(read_with_includes(ssl_path), reaction_names):
            print(
                f"Script {ssl_path.stem} uses the reaction LVARs, which modreact.h keeps at indices 0-3, "
                f"but defines {name} as {index}."
            )
            found_mismatch = True

    return found_mismatch


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
