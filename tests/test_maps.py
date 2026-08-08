"""Tests for maps.py - validates map definitions in maps.txt."""

from pathlib import Path

import maps

# The Unofficial Patch entry that drops an effect: the comma between the two is missing, so the engine
# splits on commas first, reads name "animal", and takes atoi("15 animal:10") as the chance.
MERGED_SFX = "water:40, water1:25, animal:15 animal:10, pebble:5"


def _map(index: str = "000", *, extra: str = "", **overrides: str) -> str:
    """Build one well-formed map section, so a test's edit is the only thing wrong with it."""
    keys = {
        "lookup_name": "Arroyo Bridge",
        "map_name": "ARBRIDGE",
        "music": "arroyo",
        "saved": "No",
        "can_rest_here": "Yes,Yes,Yes",
    }
    keys.update(overrides)
    body = "".join(f"{key}={value}\n" for key, value in keys.items())
    return f"[Map {index}]\n{body}{extra}"


def test_well_formed_map_has_no_problems(tmp_path: Path) -> None:
    """The builder used below is itself clean, so each failure isolates one edit."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map(), encoding="utf-8")
    assert maps.find_problems(maps_txt) == []


def test_merged_ambient_sfx_is_reported() -> None:
    """Regression: a missing comma merges two effects and the second is silently dropped."""
    problem = maps._check_ambient_sfx(MERGED_SFX)
    assert problem is not None
    assert "missing comma" in problem


def test_well_formed_ambient_sfx_is_accepted() -> None:
    """The same value with the comma restored is well formed."""
    assert maps._check_ambient_sfx("water:40, water1:25, animal:15, animal:10, pebble:5") is None


def test_too_many_ambient_sfx_is_reported() -> None:
    """Only MAP_AMBIENT_SOUND_EFFECTS_CAPACITY effects are read; the rest are dropped."""
    value = ", ".join(f"sfx{index}:10" for index in range(maps.MAX_AMBIENT_SFX + 1))
    problem = maps._check_ambient_sfx(value)
    assert problem is not None
    assert "only 7 are read" in problem


def test_unknown_key_is_reported(tmp_path: Path) -> None:
    """wmMapInit ignores keys it does not know, so a misspelling reads as a default in silence."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map(extra="state=On\n"), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "unknown key" in p]


def test_random_start_point_is_accepted(tmp_path: Path) -> None:
    """random_start_point_N is built with snprintf, so it is a real key rather than an unknown one."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map(extra="random_start_point_0=elev:0, tile_num:19086\n"), encoding="utf-8")
    assert maps.find_problems(maps_txt) == []


def test_malformed_start_point_is_reported(tmp_path: Path) -> None:
    """The pair is read as elev then tile_num, in that order."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map(extra="random_start_point_0=elev:0, tile:19086\n"), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "tile_num:<number>" in p]


def test_gap_in_start_point_numbering_is_reported(tmp_path: Path) -> None:
    """The scan stops at the first missing index, dropping every later start point."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map(extra="random_start_point_1=elev:0, tile_num:1\n"), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "without gaps" in p]


def test_unpadded_section_index_is_reported(tmp_path: Path) -> None:
    """Sections are looked up as 'Map %03d', so [Map 1] is never found and truncates the file."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map("000") + _map("1"), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "three-digit index" in p]


def test_gap_in_map_numbering_is_reported(tmp_path: Path) -> None:
    """A gap silently drops every later map."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map("000") + _map("002", lookup_name="Other"), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "expected [Map 001]" in p]


def test_duplicate_lookup_name_is_reported(tmp_path: Path) -> None:
    """city.txt entrances resolve a map by lookup_name, so a duplicate makes the target ambiguous."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map("000") + _map("001"), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "already used on line" in p]


def test_missing_required_key_is_reported(tmp_path: Path) -> None:
    """Without lookup_name the scan stops; without map_name the engine aborts."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map().replace("map_name=ARBRIDGE\n", ""), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "map_name is missing" in p]


def test_bad_can_rest_here_is_reported(tmp_path: Path) -> None:
    """can_rest_here carries one yes/no per elevation, so all three are read."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map(can_rest_here="Yes,Yes"), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "one per elevation" in p]


def test_bad_yes_no_is_reported(tmp_path: Path) -> None:
    """saved comes from a two-entry yes/no list."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map(saved="Maybe"), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "Maybe" in p]


def test_overlong_text_field_is_reported(tmp_path: Path) -> None:
    """lookup_name is copied into a fixed 40-byte buffer and would be truncated."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map(lookup_name="A" * maps.MAX_TEXT_FIELD), encoding="utf-8")
    assert [p for p in maps.find_problems(maps_txt) if "does not fit" in p]


def test_fixture_is_clean(fixtures_dir: Path) -> None:
    """Trailing ; comments and multiple start points occur in real data and are not defects."""
    assert maps.find_problems(fixtures_dir / "maps.txt") == []


def test_main_passing(fixtures_dir: Path) -> None:
    """main() reports no problem for a well-formed maps.txt."""
    assert maps.main([str(fixtures_dir / "maps.txt")]) is False


def test_main_failing(tmp_path: Path) -> None:
    """main() reports a problem when a map is malformed."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text(_map(ambient_sfx=MERGED_SFX), encoding="utf-8")
    assert maps.main([str(maps_txt)]) is True


def test_main_missing_file(tmp_path: Path) -> None:
    """A missing maps.txt is reported rather than raising."""
    assert maps.main([str(tmp_path / "nonexistent.txt")]) is True
