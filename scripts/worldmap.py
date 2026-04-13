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
ScriptNames = dict[int, str]
ScriptDescriptions = dict[int, str]
SectionLines = dict[str, int]

parser = argparse.ArgumentParser(
    description="Find discrepancies in worldmap.txt",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("worldmap", help="worldmap.txt path")
parser.add_argument("--scripts-h", dest="scripts_h", help="scripts.h path", required=False)
parser.add_argument("--scripts-lst", dest="scripts_lst", help="scripts.lst path", required=False)
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
            content = allow_set.split("#", 1)[0].split(";", 1)[0].strip()
            if not content:
                continue
            allow_list = [item.strip() for item in content.split(",") if item.strip()]
            # Convert to int for proper numeric sorting
            allow_list_int = sorted(int(x) for x in allow_list)
            allowed_script_sets.append(allow_list_int)
    return allowed_script_sets


def get_script_names(scripts_h_path: Path | None) -> ScriptNames:
    """Parse scripts.h and return a map of script number to symbolic name."""
    if scripts_h_path is None or not scripts_h_path.exists():
        return {}

    script_names: ScriptNames = {}
    pattern = re.compile(r"#define\s+(\S+)\s+\((\d+)\)")
    for line in scripts_h_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.search(line)
        if match:
            script_names[int(match.group(2))] = match.group(1)
    return script_names


def get_script_descriptions(scripts_lst_path: Path | None) -> ScriptDescriptions:
    """Parse scripts.lst and return a map of script number to human description."""
    if scripts_lst_path is None or not scripts_lst_path.exists():
        return {}

    script_descriptions: ScriptDescriptions = {}
    for index, line in enumerate(scripts_lst_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        _, _, comment = line.partition(";")
        description = comment.split("#", 1)[0].strip()
        if description:
            script_descriptions[index] = description
    return script_descriptions


def get_section_lines(worldmap_path: Path) -> SectionLines:
    """Return the source line number for each INI section header."""
    section_lines: SectionLines = {}
    for line_number, line in enumerate(worldmap_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section_lines[stripped[1:-1]] = line_number
    return section_lines


def format_script_combination(
    section: str,
    line_number: int | None,
    scripts: ScriptSet,
    script_names: ScriptNames,
    script_descriptions: ScriptDescriptions,
) -> str:
    """Format a script combination using one indented line per script."""
    number_width = max(len(str(script_num)) for script_num in scripts)
    location = f" (line {line_number})" if line_number is not None else ""
    lines = [f"{section}{location} script combination is not allowed:"]
    for script_num in scripts:
        script_name = script_names.get(script_num, "<unknown>")
        script_description = script_descriptions.get(script_num, "<unknown>")
        lines.append(f'  {script_num:<{number_width}} = {script_name} = "{script_description}"')
    return "\n".join(lines)


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

    script_names = get_script_names(Path(args.scripts_h) if args.scripts_h else None)
    script_descriptions = get_script_descriptions(Path(args.scripts_lst) if args.scripts_lst else None)
    section_lines = get_section_lines(worldmap_path)

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
                print(
                    format_script_combination(
                        section,
                        section_lines.get(section),
                        scripts_list,
                        script_names,
                        script_descriptions,
                    )
                )
                error = True
    if error:
        sys.exit(1)


if __name__ == "__main__":
    main()
