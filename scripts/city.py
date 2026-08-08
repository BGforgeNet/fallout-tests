#!/usr/bin/env python3
"""Validate area definitions in city.txt.

Field layout and value ranges follow wmAreaInit in fallout2-ce src/worldmap.cc. Two of its behaviours
make malformed data hard to notice, so they drive most of the checks here:

- An entrance_N entry is read as exactly seven comma-separated fields and anything past the seventh is
  ignored, so a stray field loads without error while shifting elevation, tile and rotation.
- Areas are scanned as "Area 00", "Area 01", ... and the scan stops at the first section it cannot find
  or whose townmap_art_idx is missing, so a misnumbered section silently drops every area after it.

city.txt is UTF-8/ASCII.
"""

import argparse
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
import re
import sys

import maps

# Field layout of entrance_N, from EntranceInfo in fallout2-ce src/worldmap.cc.
ENTRANCE_FIELDS = ("state", "x", "y", "map", "elevation", "tile", "rotation")
WORLD_POS_FIELDS = ("x", "y")
# wmStateStrs and wmAreaSizeStrs; the data spells them capitalised.
VALID_STATES = frozenset({"on", "off"})
VALID_SIZES = frozenset({"small", "medium", "large"})
# ROTATION_NE through ROTATION_NW, i.e. ROTATION_COUNT - 1 (src/obj_types.h).
MAX_ROTATION = 5
# CITY_NAME_SIZE and ENTRANCE_LIST_CAPACITY (src/worldmap.cc).
MAX_AREA_NAME = 40
MAX_ENTRANCES = 10
# Keys wmAreaInit refuses to start without.
REQUIRED_KEYS = ("townmap_art_idx", "area_name", "world_pos", "start_state", "size")

_SECTION_RE = re.compile(r"^\[(?P<name>[^]]*)\]")
_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*)$")
_AREA_NAME_RE = re.compile(r"^Area (?P<index>\d{2})$")
_ENTRANCE_KEY_RE = re.compile(r"^entrance_(?P<index>\d+)$", re.IGNORECASE)

parser = argparse.ArgumentParser(
    description="Find malformed area definitions in city.txt",
)

parser.add_argument("CITY_TXT", help="city.txt path")
parser.add_argument(
    "--maps",
    dest="maps_txt",
    help="maps.txt path; when given, entrance map names are resolved against its lookup_name entries",
    required=False,
)


@dataclass
class Entry:
    """One key=value line inside an area."""

    key: str
    value: str
    line: int


@dataclass
class Area:
    """One [Area NN] section and the entries below it."""

    name: str
    line: int
    entries: list[Entry] = field(default_factory=list)


def _check_int(value: str) -> str | None:
    """Reject a value the engine's strParseInt would not accept."""
    try:
        int(value)
    except ValueError:
        return f"{value!r} is not a number"
    return None


def _check_state(value: str) -> str | None:
    """Reject a value outside the two-entry on/off list."""
    if value.lower() not in VALID_STATES:
        return f"{value!r} is not one of {sorted(VALID_STATES)}"
    return None


def _check_size(value: str) -> str | None:
    """Reject a value outside the three-entry size list."""
    if value.lower() not in VALID_SIZES:
        return f"{value!r} is not one of {sorted(VALID_SIZES)}"
    return None


def _check_world_pos(value: str) -> str | None:
    """world_pos is two integers; the engine parses x then y and fails on either."""
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != len(WORLD_POS_FIELDS):
        expected = ", ".join(WORLD_POS_FIELDS)
        return f"expected {len(WORLD_POS_FIELDS)} fields ({expected}), got {len(parts)}"
    for name, part in zip(WORLD_POS_FIELDS, parts, strict=True):
        problem = _check_int(part)
        if problem:
            return f"{name} {problem}"
    return None


def _check_area_name(value: str) -> str | None:
    """area_name is copied into a fixed 40-byte buffer, so a longer name is truncated."""
    if not value:
        return "is empty"
    if len(value) >= MAX_AREA_NAME:
        return f"is {len(value)} characters, which does not fit in {MAX_AREA_NAME} bytes"
    return None


_KEY_CHECKS: dict[str, Callable[[str], str | None]] = {
    "townmap_art_idx": _check_int,
    "townmap_label_art_idx": _check_int,
    "area_name": _check_area_name,
    "world_pos": _check_world_pos,
    "start_state": _check_state,
    "lock_state": _check_state,
    "size": _check_size,
}


def check_entrance(value: str) -> str | None:
    """Describe what is wrong with one entrance value.

    Args:
        value: The right-hand side of an entrance_N entry, comments already stripped

    Returns:
        A description of the first problem found, or None if the entry is well formed
    """
    fields = [item.strip() for item in value.split(",")]
    if len(fields) != len(ENTRANCE_FIELDS):
        expected = ", ".join(ENTRANCE_FIELDS)
        return f"expected {len(ENTRANCE_FIELDS)} fields ({expected}), got {len(fields)}"

    state, x, y, map_name, elevation, tile, rotation = fields
    problem = _check_state(state)
    if problem:
        return f"state {problem}"
    if not map_name:
        return "map name is empty"

    numbers: dict[str, int] = {}
    for name, raw in (("x", x), ("y", y), ("elevation", elevation), ("tile", tile), ("rotation", rotation)):
        problem = _check_int(raw)
        if problem:
            return f"{name} {problem}"
        numbers[name] = int(raw)

    if not 0 <= numbers["rotation"] <= MAX_ROTATION:
        return f"rotation {numbers['rotation']} is outside 0-{MAX_ROTATION}"
    return None


def parse_areas(text: str) -> list[Area]:
    """Split city.txt into areas and their entries, keeping line numbers for reporting.

    Args:
        text: Full contents of city.txt

    Returns:
        One Area per section header, in file order
    """
    areas: list[Area] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith(";"):
            continue

        section_match = _SECTION_RE.match(line)
        if section_match:
            areas.append(Area(name=section_match.group("name").strip(), line=line_number))
            continue

        key_match = _KEY_RE.match(line)
        if not key_match or not areas:
            continue

        # Trailing ; comments are common in this file and are not part of the value.
        value = key_match.group("value").split(";", 1)[0].strip()
        areas[-1].entries.append(Entry(key=key_match.group("key"), value=value, line=line_number))

    return areas


def check_area(area: Area) -> list[tuple[int, str]]:
    """Check one area's keys, values and entrance numbering.

    Args:
        area: A parsed area section

    Returns:
        (line number, message) per problem found
    """
    problems: list[tuple[int, str]] = []
    seen: dict[str, Entry] = {}
    entrance_indices: list[int] = []

    for entry in area.entries:
        entrance_match = _ENTRANCE_KEY_RE.match(entry.key)
        if entrance_match:
            entrance_indices.append(int(entrance_match.group("index")))
            problem = check_entrance(entry.value)
            if problem:
                problems.append((entry.line, f"{entry.key}: {problem}"))
        else:
            check = _KEY_CHECKS.get(entry.key)
            if check:
                problem = check(entry.value)
                if problem:
                    problems.append((entry.line, f"{entry.key}: {problem}"))
        if entry.key in seen:
            problems.append((entry.line, f"{entry.key}: already set on line {seen[entry.key].line}"))
        seen[entry.key] = entry

    for key in REQUIRED_KEYS:
        if key not in seen:
            problems.append((area.line, f"{key} is missing"))

    problems.extend(_check_entrance_numbering(area, entrance_indices))
    return problems


def _check_entrance_numbering(area: Area, indices: list[int]) -> list[tuple[int, str]]:
    """Entrances are read as entrance_0, entrance_1, ... and the scan stops at the first gap."""
    problems: list[tuple[int, str]] = []
    if sorted(indices) != list(range(len(indices))):
        got = ", ".join(str(index) for index in sorted(indices))
        problems.append((area.line, f"entrance indices must run from 0 without gaps, got {got}"))
    if len(indices) > MAX_ENTRANCES:
        problems.append((area.line, f"has {len(indices)} entrances, but only {MAX_ENTRANCES} are read"))
    return problems


def check_area_sequence(areas: list[Area]) -> list[tuple[int, str]]:
    """Sections must be Area 00, Area 01, ... contiguously; the engine stops at the first gap.

    Args:
        areas: Parsed areas in file order

    Returns:
        (line number, message) per problem found
    """
    problems: list[tuple[int, str]] = []
    expected = 0
    for area in areas:
        name_match = _AREA_NAME_RE.match(area.name)
        if not name_match:
            problems.append((area.line, f"[{area.name}]: section name must be 'Area NN' with a two-digit index"))
            continue
        index = int(name_match.group("index"))
        if index != expected:
            problems.append((area.line, f"[{area.name}]: expected [Area {expected:02d}]; later areas are not read"))
            expected = index
        expected += 1
    return problems


def check_entrance_maps(areas: list[Area], known_maps: dict[str, int]) -> list[tuple[int, str]]:
    """Every entrance names a map that maps.txt must declare.

    wmParseFindMapIdxMatch compares the name case-insensitively against each lookup_name and returns -1
    when none matches, which aborts wmAreaInit - so an unknown name is a hard load failure, not a shift.

    Args:
        areas: Parsed areas in file order
        known_maps: Lowercased lookup_name to declaring line, from maps.lookup_names()

    Returns:
        (line number, message) per entrance naming a map that maps.txt does not declare
    """
    problems: list[tuple[int, str]] = []
    for area in areas:
        for entry in area.entries:
            if not _ENTRANCE_KEY_RE.match(entry.key):
                continue
            fields = [item.strip() for item in entry.value.split(",")]
            map_index = ENTRANCE_FIELDS.index("map")
            if len(fields) <= map_index:
                # Too short to hold a map name at all; the field count is reported separately.
                continue
            # The engine reads this position whatever follows it, so a stray later field does not
            # move the map name - check it even when the field count is already wrong.
            map_name = fields[map_index]
            if map_name and map_name.lower() not in known_maps:
                message = f"[{area.name}] {entry.key}: map {map_name!r} is not declared in maps.txt"
                problems.append((entry.line, message))
    return problems


def find_problems(city_path: str | Path, maps_path: str | Path | None = None) -> list[str]:
    """Check every area in city.txt.

    Args:
        city_path: Path to city.txt
        maps_path: Optional maps.txt, enabling the entrance map name cross-reference

    Returns:
        One message per problem, naming the file, line number and area
    """
    city_path = Path(city_path)
    areas = parse_areas(city_path.read_text(encoding="utf-8", errors="replace"))

    located: list[tuple[int, str]] = list(check_area_sequence(areas))
    for area in areas:
        located.extend((line, f"[{area.name}] {message}") for line, message in check_area(area))
    if maps_path is not None:
        located.extend(check_entrance_maps(areas, maps.lookup_names(maps_path)))

    return [f"{city_path}:{line}: {message}" for line, message in sorted(located)]


def main(argv: list[str] | None = None) -> bool:
    """Main entry point for city.txt validation.

    Returns:
        True if city.txt is unreadable or any area is malformed. The caller owns the exit code.
    """
    args = parser.parse_args(argv)
    city_path = Path(args.CITY_TXT)
    if not city_path.exists():
        print(f"{args.CITY_TXT} does not exist.")
        return True
    if not city_path.is_file():
        print(f"{args.CITY_TXT} is not a file")
        return True

    maps_path = Path(args.maps_txt) if args.maps_txt else None
    if maps_path is not None and not maps_path.is_file():
        print(f"{args.maps_txt} does not exist.")
        return True

    problems = find_problems(city_path, maps_path)
    for problem in problems:
        print(problem)
    return bool(problems)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
