#!/usr/bin/env python3
"""Validate map definitions in maps.txt.

Field layout and value ranges follow wmMapInit in fallout2-ce src/worldmap.cc. Three of its behaviours
make malformed data hard to notice:

- Maps are scanned as "Map 000", "Map 001", ... and the scan stops at the first section that is missing
  or has no lookup_name, so a misnumbered section silently drops every map after it.
- ambient_sfx entries are split on commas and then at the first colon, and the chance is read with atoi.
  A missing comma therefore merges two effects into one and the second is silently lost.
- Unknown keys are ignored outright, so a misspelled key reads as a default with no warning.

maps.txt is UTF-8/ASCII.
"""

import argparse
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import re
import sys

# wmYesNoStrs in fallout2-ce src/worldmap.cc; the data spells them lowercase.
VALID_YES_NO = frozenset({"yes", "no"})
# MapInfo's fixed buffers and MAP_AMBIENT_SOUND_EFFECTS_CAPACITY (src/worldmap.cc).
MAX_TEXT_FIELD = 40
MAX_AMBIENT_SFX = 7
# can_rest_here carries one yes/no per elevation.
REST_ELEVATIONS = 3
# MAP_STARTING_POINTS_CAPACITY, counted across every random_start_point_N of one map.
MAX_START_POINTS = 15
# wmMapInit stops scanning without lookup_name and aborts without map_name.
REQUIRED_KEYS = ("lookup_name", "map_name")

_SECTION_RE = re.compile(r"^\[(?P<name>[^]]*)\]")
_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*)$")
_MAP_NAME_RE = re.compile(r"^Map (?P<index>\d{3})$")
_START_POINT_RE = re.compile(r"^random_start_point_(?P<index>\d+)$", re.IGNORECASE)

parser = argparse.ArgumentParser(
    description="Find malformed map definitions in maps.txt",
)

parser.add_argument("MAPS_TXT", help="maps.txt path")


@dataclass
class Entry:
    """One key=value line inside a map."""

    key: str
    value: str
    line: int


@dataclass
class MapSection:
    """One [Map NNN] section and the entries below it."""

    name: str
    line: int
    entries: list[Entry] = field(default_factory=list)


def _check_text(value: str) -> str | None:
    """Reject a value that would not fit the fixed 40-byte buffer it is copied into."""
    if not value:
        return "is empty"
    if len(value) >= MAX_TEXT_FIELD:
        return f"is {len(value)} characters, which does not fit in {MAX_TEXT_FIELD} bytes"
    return None


def _check_yes_no(value: str) -> str | None:
    """Reject a value outside the two-entry yes/no list."""
    if value.lower() not in VALID_YES_NO:
        return f"{value!r} is not one of {sorted(VALID_YES_NO)}"
    return None


def _check_can_rest_here(value: str) -> str | None:
    """can_rest_here is one yes/no per elevation, so all three are read."""
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != REST_ELEVATIONS:
        return f"expected {REST_ELEVATIONS} yes/no values, one per elevation, got {len(parts)}"
    for elevation, part in enumerate(parts):
        problem = _check_yes_no(part)
        if problem:
            return f"elevation {elevation} {problem}"
    return None


def _check_ambient_sfx(value: str) -> str | None:
    """Each entry is name:chance; the engine splits on commas first, so a missing one merges two."""
    entries = [entry.strip() for entry in value.split(",") if entry.strip()]
    if len(entries) > MAX_AMBIENT_SFX:
        return f"has {len(entries)} effects, but only {MAX_AMBIENT_SFX} are read"
    for entry in entries:
        name, separator, chance = entry.partition(":")
        if not separator:
            return f"{entry!r} is not name:chance"
        if not name.strip():
            return f"{entry!r} has an empty name"
        try:
            int(chance.strip())
        except ValueError:
            return f"{entry!r} chance {chance.strip()!r} is not a number; a missing comma merges two effects"
    return None


def _check_start_point(value: str) -> str | None:
    """Each start point is an elev:N, tile_num:M pair, read in that order until the value runs out."""
    segments = [segment.strip() for segment in value.split(",") if segment.strip()]
    if not segments:
        return "is empty"
    if len(segments) % 2 != 0:
        return f"expected elev/tile_num pairs, got {len(segments)} values"
    for position, segment in enumerate(segments):
        wanted = "elev" if position % 2 == 0 else "tile_num"
        name, separator, number = segment.partition(":")
        if not separator or name.strip().lower() != wanted:
            return f"{segment!r} should be {wanted}:<number>"
        try:
            int(number.strip())
        except ValueError:
            return f"{segment!r} value {number.strip()!r} is not a number"
    return None


def _count_start_points(value: str) -> int:
    """How many start points one random_start_point_N value contributes."""
    return len([segment for segment in value.split(",") if segment.strip()]) // 2


_KEY_CHECKS: dict[str, Callable[[str], str | None]] = {
    "lookup_name": _check_text,
    "map_name": _check_text,
    "music": _check_text,
    "ambient_sfx": _check_ambient_sfx,
    "can_rest_here": _check_can_rest_here,
    "saved": _check_yes_no,
    "dead_bodies_age": _check_yes_no,
    "pipboy_active": _check_yes_no,
    "automap": _check_yes_no,
}


def parse_maps(text: str) -> list[MapSection]:
    """Split maps.txt into map sections and their entries, keeping line numbers for reporting.

    Args:
        text: Full contents of maps.txt

    Returns:
        One MapSection per section header, in file order
    """
    sections: list[MapSection] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith(";"):
            continue

        section_match = _SECTION_RE.match(line)
        if section_match:
            sections.append(MapSection(name=section_match.group("name").strip(), line=line_number))
            continue

        key_match = _KEY_RE.match(line)
        if not key_match or not sections:
            continue

        # Trailing ; comments are common in this file and are not part of the value.
        value = key_match.group("value").split(";", 1)[0].strip()
        sections[-1].entries.append(Entry(key=key_match.group("key"), value=value, line=line_number))

    return sections


def check_map(section: MapSection) -> list[tuple[int, str]]:
    """Check one map's keys and values.

    Args:
        section: A parsed map section

    Returns:
        (line number, message) per problem found
    """
    problems: list[tuple[int, str]] = []
    seen: dict[str, Entry] = {}
    start_indices: list[int] = []
    start_points = 0

    for entry in section.entries:
        start_match = _START_POINT_RE.match(entry.key)
        if start_match:
            start_indices.append(int(start_match.group("index")))
            start_points += _count_start_points(entry.value)
            problem = _check_start_point(entry.value)
        else:
            # wmMapInit ignores keys it does not know, so a misspelling reads as a default in silence.
            # A new sfall extension lands here too, and is a signal to add it to _KEY_CHECKS.
            check = _KEY_CHECKS.get(entry.key)
            problem = check(entry.value) if check else "unknown key, the engine ignores it"
        if problem:
            problems.append((entry.line, f"{entry.key}: {problem}"))
        if entry.key in seen:
            problems.append((entry.line, f"{entry.key}: already set on line {seen[entry.key].line}"))
        seen[entry.key] = entry

    for key in REQUIRED_KEYS:
        if key not in seen:
            problems.append((section.line, f"{key} is missing"))

    problems.extend(_check_start_point_numbering(section, start_indices, start_points))
    return problems


def _check_start_point_numbering(section: MapSection, indices: list[int], total: int) -> list[tuple[int, str]]:
    """Start points are read as random_start_point_0, _1, ... and the scan stops at the first gap."""
    problems: list[tuple[int, str]] = []
    if sorted(indices) != list(range(len(indices))):
        got = ", ".join(str(index) for index in sorted(indices))
        problems.append((section.line, f"random_start_point indices must run from 0 without gaps, got {got}"))
    if total > MAX_START_POINTS:
        problems.append((section.line, f"has {total} start points, but only {MAX_START_POINTS} are read"))
    return problems


def check_map_sequence(sections: list[MapSection]) -> list[tuple[int, str]]:
    """Sections must be Map 000, Map 001, ... contiguously; the engine stops at the first gap.

    Args:
        sections: Parsed map sections in file order

    Returns:
        (line number, message) per problem found
    """
    problems: list[tuple[int, str]] = []
    expected = 0
    for section in sections:
        name_match = _MAP_NAME_RE.match(section.name)
        if not name_match:
            problems.append(
                (section.line, f"[{section.name}]: section name must be 'Map NNN' with a three-digit index")
            )
            continue
        index = int(name_match.group("index"))
        if index != expected:
            problems.append((section.line, f"[{section.name}]: expected [Map {expected:03d}]; later maps are not read"))
            expected = index
        expected += 1
    return problems


def check_lookup_names(sections: list[MapSection]) -> list[tuple[int, str]]:
    """city.txt entrances resolve a map by lookup_name, so a duplicate makes the target ambiguous."""
    problems: list[tuple[int, str]] = []
    seen: dict[str, int] = {}
    for section in sections:
        for entry in section.entries:
            if entry.key != "lookup_name":
                continue
            key = entry.value.lower()
            if key in seen:
                problems.append((entry.line, f"lookup_name {entry.value!r} already used on line {seen[key]}"))
            else:
                seen[key] = entry.line
    return problems


def find_problems(maps_path: str | Path) -> list[str]:
    """Check every map in maps.txt.

    Args:
        maps_path: Path to maps.txt

    Returns:
        One message per problem, naming the file, line number and map
    """
    maps_path = Path(maps_path)
    sections = parse_maps(maps_path.read_text(encoding="utf-8", errors="replace"))

    located: list[tuple[int, str]] = list(check_map_sequence(sections))
    located.extend(check_lookup_names(sections))
    for section in sections:
        located.extend((line, f"[{section.name}] {message}") for line, message in check_map(section))

    return [f"{maps_path}:{line}: {message}" for line, message in sorted(located)]


def main(argv: list[str] | None = None) -> bool:
    """Main entry point for maps.txt validation.

    Returns:
        True if maps.txt is unreadable or any map is malformed. The caller owns the exit code.
    """
    args = parser.parse_args(argv)
    maps_path = Path(args.MAPS_TXT)
    if not maps_path.exists():
        print(f"{args.MAPS_TXT} does not exist.")
        return True
    if not maps_path.is_file():
        print(f"{args.MAPS_TXT} is not a file")
        return True

    problems = find_problems(maps_path)
    for problem in problems:
        print(problem)
    return bool(problems)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
