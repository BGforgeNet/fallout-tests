#!/usr/bin/env python3
"""Validate worldmap encounter configurations for Fallout.

This module checks that encounter scripts follow allowed combinations,
preventing invalid script sets from appearing together in encounters,
that every encounter an encounter table names is defined, and that every
encounter script number is within scripts.lst.
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

ENCOUNTER_PREFIX = "Encounter: "
# The engine builds the section name "Encounter: <name>" in a 40-byte buffer (wmReadEncBaseType), so a longer
# name is cut short and never found.
MAX_ENCOUNTER_NAME = 40 - 1 - len(ENCOUNTER_PREFIX)
_COUNT_RE = re.compile(r"\(\s*\d+\s*(?:-\s*\d+\s*)?\)")

parser = argparse.ArgumentParser(
    description="Find discrepancies in worldmap.txt",
)

parser.add_argument("worldmap", help="worldmap.txt path")
parser.add_argument("--scripts-h", dest="scripts_h", help="scripts.h path", required=False)
parser.add_argument("--scripts-lst", dest="scripts_lst", help="scripts.lst path", required=False)
parser.add_argument(
    "-s",
    dest="script_sets",
    help="allow a set of scripts to appear in an encounter together; repeat per set: '-s 100,101 -s 200,201,202'",
    action="append",
    required=False,
)


def get_allowed_script_sets(script_sets: list[str] | None) -> AllowedScriptSets:
    """Parse command line script set arguments to extract allowed script sets.

    Args:
        script_sets: One entry per -s occurrence, or None if the flag was not given

    Returns:
        List of script sets where each set is a list of script numbers

    Raises:
        ValueError: a -s value does not hold a comma-separated list of script numbers.
    """
    allowed_script_sets: AllowedScriptSets = []
    for allow_set in script_sets or []:
        content = allow_set.split("#", 1)[0].split(";", 1)[0].strip()
        if not content:
            continue
        allow_list = [item.strip() for item in content.split(",") if item.strip()]
        try:
            # Convert to int for proper numeric sorting
            allow_list_int = sorted(int(x) for x in allow_list)
        except ValueError as exc:
            raise ValueError(f"-s {content!r}: expected comma-separated script numbers") from exc
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
    for line_number, line in enumerate(
        worldmap_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
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


def get_table_encounter_names(value: str) -> list[str]:
    """Return the encounter names in an encounter table entry, as the engine reads its Enc: part.

    The Enc: part runs to the next comma; it alternates a name, optionally preceded by a (min-max) count,
    with a situation word (wmParseEncounterSubEncStr).

    Args:
        value: The entry value, such as "Chance:5%,Enc:(2-4) Raiders AMBUSH Player,If(...)"

    Returns:
        The names in order, including "Player"; empty when the entry has no Enc: part
    """
    match = re.search(r"enc:([^,]*)", value.split(";", 1)[0], re.I)
    if not match:
        return []
    return _COUNT_RE.sub(" ", match[1]).split()[0::2]


def check_table_encounters(wmap: configparser.ConfigParser, section_lines: SectionLines) -> list[str]:
    """Report encounter table entries naming an encounter that has no usable section.

    The engine stops reading an entry at a name it cannot find and keeps the entry, so the later groups,
    the scenery and the If() condition are silently dropped (wmParseEncounterTableIndex).

    Returns:
        One message per bad name
    """
    defined = {
        section[len(ENCOUNTER_PREFIX) :].lower()
        for section in wmap.sections()
        if section.startswith(ENCOUNTER_PREFIX) and wmap.has_option(section, "type_00")
    }
    errors = []
    for section in wmap.sections():
        if not section.startswith("Encounter Table"):
            continue
        for option in wmap.options(section):
            if not option.startswith("enc_"):
                continue
            for name in get_table_encounter_names(wmap.get(section, option)):
                if name.lower() == "player":
                    continue
                where = f"{section} (line {section_lines.get(section)}) {option}"
                if len(name) > MAX_ENCOUNTER_NAME:
                    errors.append(f"{where}: encounter name {name} is longer than {MAX_ENCOUNTER_NAME} characters.")
                elif name.lower() not in defined:
                    errors.append(f"{where}: encounter {name} has no [{ENCOUNTER_PREFIX}{name}] section with type_00.")
    return errors


def check_script_numbers(wmap: configparser.ConfigParser, section_lines: SectionLines, script_count: int) -> list[str]:
    """Report encounter critters whose Script:N is not a scripts.lst line; the engine uses N - 1 as the index.

    Returns:
        One message per bad script number
    """
    errors = []
    for section in wmap.sections():
        if not section.startswith(ENCOUNTER_PREFIX):
            continue
        for option in wmap.options(section):
            for number in re.findall(r"Script:\s*(\d+)", wmap.get(section, option).split(";", 1)[0]):
                if not 1 <= int(number) <= script_count:
                    errors.append(
                        f"{section} (line {section_lines.get(section)}) {option}: Script:{number} is outside "
                        f"scripts.lst, which has {script_count} lines."
                    )
    return errors


def main(argv: list[str] | None = None) -> bool:
    """Main entry point for worldmap validation.

    Returns:
        True if the worldmap is unreadable, holds a disallowed combination, names an undefined encounter, or uses a
        script number outside scripts.lst. The caller owns the exit code.
    """
    args = parser.parse_args(argv)
    error = False
    try:
        allowed_sets = get_allowed_script_sets(args.script_sets)
    except ValueError as exc:
        print(exc)
        return True

    worldmap_path = Path(args.worldmap)
    if not worldmap_path.exists():
        print(f"{args.worldmap} does not exist.")
        return True
    if not worldmap_path.is_file():
        print(f"{args.worldmap} is not a file")
        return True

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

    errors = check_table_encounters(wmap, section_lines)
    if args.scripts_lst and Path(args.scripts_lst).is_file():
        script_count = len(Path(args.scripts_lst).read_text(encoding="utf-8", errors="replace").splitlines())
        errors += check_script_numbers(wmap, section_lines, script_count)
    for message in errors:
        print(message)
    return error or bool(errors)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
