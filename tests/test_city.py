"""Tests for city.py - validates area entrance definitions in city.txt."""

from pathlib import Path

import city

# The exact entry from Fallout2_Restoration_Project issue 388: a leading 0 was inserted after the map
# name, so the engine read elevation=0, tile=-1, rotation=-1 and the entrance faced an invalid direction.
SHIFTED_ENTRANCE = "On,345,230,New Reno Golgatha,0,-1,-1,0"
CORRECT_ENTRANCE = "On,345,230,New Reno Golgatha,-1,-1,0"


def test_shifted_entrance_is_reported() -> None:
    """Regression: an extra field shifts elevation/tile/rotation and the engine loads it silently."""
    problem = city.check_entrance(SHIFTED_ENTRANCE)
    assert problem is not None
    assert "got 8" in problem


def test_corrected_entrance_is_accepted() -> None:
    """The same entry with the stray field removed is well formed."""
    assert city.check_entrance(CORRECT_ENTRANCE) is None


def test_too_few_fields_is_reported() -> None:
    """A missing field is caught too; the engine fails to load the area entirely."""
    problem = city.check_entrance("On,345,230,New Reno Golgatha,-1,0")
    assert problem is not None
    assert "got 6" in problem


def test_rotation_upper_bound_is_accepted() -> None:
    """Rotation 5 is ROTATION_NW, the highest valid direction."""
    assert city.check_entrance("On,345,230,Map,-1,-1,5") is None


def test_rotation_above_range_is_reported() -> None:
    """Rotation 6 is ROTATION_COUNT, one past the last valid direction."""
    problem = city.check_entrance("On,345,230,Map,-1,-1,6")
    assert problem == "rotation 6 is outside 0-5"


def test_negative_rotation_is_reported() -> None:
    """A field count can be right while rotation is still invalid, so it is checked separately."""
    problem = city.check_entrance("On,345,230,Map,-1,-1,-1")
    assert problem == "rotation -1 is outside 0-5"


def test_unknown_state_is_reported() -> None:
    """State comes from a two-entry list; anything else fails to load in the engine."""
    problem = city.check_entrance("Maybe,345,230,Map,-1,-1,0")
    assert problem is not None
    assert "Maybe" in problem


def test_state_is_case_insensitive() -> None:
    """The data spells states capitalised, the engine compares lowercase."""
    assert city.check_entrance("oFf,345,230,Map,-1,-1,0") is None


def test_non_numeric_field_is_reported() -> None:
    """A non-numeric coordinate names the offending field rather than raising."""
    problem = city.check_entrance("On,345,y230,Map,-1,-1,0")
    assert problem is not None
    assert "y230" in problem


def test_padded_fields_are_accepted() -> None:
    """Real entries pad values with spaces; padding is not a defect."""
    assert city.check_entrance("On, 345 , 230 , Map , -1 , -1 , 3 ") is None


def _area(index: str = "00", *, extra: str = "", **overrides: str) -> str:
    """Build one well-formed area section, so a test's edit is the only thing wrong with it."""
    keys = {
        "area_name": "Golgotha",
        "world_pos": "935,992",
        "start_state": "Off",
        "size": "Small",
        "townmap_art_idx": "-1",
        "townmap_label_art_idx": "-1",
        "entrance_0": CORRECT_ENTRANCE,
    }
    keys.update(overrides)
    body = "".join(f"{key}={value}\n" for key, value in keys.items())
    return f"[Area {index}]\n{body}{extra}"


def test_well_formed_area_has_no_problems(tmp_path: Path) -> None:
    """The builder used by the tests below is itself clean, so each failure isolates one edit."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(), encoding="utf-8")
    assert city.find_problems(city_txt) == []


def test_find_problems_reports_line_and_area(tmp_path: Path) -> None:
    """A problem names the file, line number and area so it can be fixed without searching."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area("00", entrance_0=SHIFTED_ENTRANCE), encoding="utf-8")
    problems = city.find_problems(city_txt)
    assert len(problems) == 1
    assert problems[0].startswith(f"{city_txt}:8: [Area 00] entrance_0: ")


def test_missing_required_key_is_reported(tmp_path: Path) -> None:
    """wmAreaInit refuses to start without world_pos, so its absence is a defect not a default."""
    city_txt = tmp_path / "city.txt"
    body = _area().replace("world_pos=935,992\n", "")
    city_txt.write_text(body, encoding="utf-8")
    assert [p for p in city.find_problems(city_txt) if "world_pos is missing" in p]


def test_unpadded_section_index_is_reported(tmp_path: Path) -> None:
    """Sections are looked up as 'Area %02d', so [Area 1] is never found and truncates the file."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area("00") + _area("1"), encoding="utf-8")
    assert [p for p in city.find_problems(city_txt) if "two-digit index" in p]


def test_gap_in_area_numbering_is_reported(tmp_path: Path) -> None:
    """The scan stops at the first missing index, silently dropping every later area."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area("00") + _area("02"), encoding="utf-8")
    assert [p for p in city.find_problems(city_txt) if "expected [Area 01]" in p]


def test_gap_in_entrance_numbering_is_reported(tmp_path: Path) -> None:
    """Entrances are read as entrance_0, entrance_1, ... and the scan stops at the first gap."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(extra=f"entrance_2={CORRECT_ENTRANCE}\n"), encoding="utf-8")
    assert [p for p in city.find_problems(city_txt) if "without gaps" in p]


def test_too_many_entrances_is_reported(tmp_path: Path) -> None:
    """Only ENTRANCE_LIST_CAPACITY entrances are read; the rest are silently dropped."""
    city_txt = tmp_path / "city.txt"
    extra = "".join(f"entrance_{index}={CORRECT_ENTRANCE}\n" for index in range(1, city.MAX_ENTRANCES + 1))
    city_txt.write_text(_area(extra=extra), encoding="utf-8")
    assert [p for p in city.find_problems(city_txt) if "only 10 are read" in p]


def test_duplicate_key_is_reported(tmp_path: Path) -> None:
    """A repeated key means one of the two values is silently ignored."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(extra="size=Large\n"), encoding="utf-8")
    assert [p for p in city.find_problems(city_txt) if "already set on line" in p]


def test_bad_size_is_reported(tmp_path: Path) -> None:
    """size comes from a three-entry list."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(size="Enormous"), encoding="utf-8")
    assert [p for p in city.find_problems(city_txt) if "Enormous" in p]


def test_bad_world_pos_is_reported(tmp_path: Path) -> None:
    """world_pos is exactly two integers."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(world_pos="935,992,7"), encoding="utf-8")
    assert [p for p in city.find_problems(city_txt) if "got 3" in p]


def test_overlong_area_name_is_reported(tmp_path: Path) -> None:
    """area_name is copied into a fixed 40-byte buffer and would be truncated."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(area_name="G" * city.MAX_AREA_NAME), encoding="utf-8")
    assert [p for p in city.find_problems(city_txt) if "does not fit" in p]


def test_find_problems_ignores_comments(fixtures_dir: Path) -> None:
    """Commented-out entrances and trailing ; comments appear in real data and are not defects."""
    assert city.find_problems(fixtures_dir / "city.txt") == []


def test_main_passing(fixtures_dir: Path) -> None:
    """main() reports no problem for a well-formed city.txt."""
    assert city.main([str(fixtures_dir / "city.txt")]) is False


def test_main_failing(tmp_path: Path) -> None:
    """main() reports a problem when an entrance is malformed."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(f"[Area 1]\nentrance_0={SHIFTED_ENTRANCE}\n", encoding="utf-8")
    assert city.main([str(city_txt)]) is True


def test_entrance_map_name_is_resolved_against_maps(tmp_path: Path, fixtures_dir: Path) -> None:
    """wmParseFindMapIdxMatch aborts the whole city load when a name matches no lookup_name."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(entrance_0="On,345,230,No Such Map,-1,-1,0"), encoding="utf-8")
    problems = city.find_problems(city_txt, fixtures_dir / "maps.txt")
    assert [p for p in problems if "'No Such Map' is not declared in maps.txt" in p]


def test_known_entrance_map_name_is_accepted(tmp_path: Path, fixtures_dir: Path) -> None:
    """The comparison is case-insensitive, matching compat_stricmp in the engine."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(entrance_0="On,345,230,ARROYO BRIDGE,-1,-1,0"), encoding="utf-8")
    assert city.find_problems(city_txt, fixtures_dir / "maps.txt") == []


def test_map_name_checked_even_when_field_count_is_wrong(tmp_path: Path, fixtures_dir: Path) -> None:
    """A stray field lands after the map name, so the engine still reads position 3 as the map."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(entrance_0="On,345,230,No Such Map,0,-1,-1,0"), encoding="utf-8")
    problems = city.find_problems(city_txt, fixtures_dir / "maps.txt")
    assert [p for p in problems if "not declared in maps.txt" in p]
    assert [p for p in problems if "got 8" in p]


def test_cross_reference_is_skipped_without_maps(tmp_path: Path) -> None:
    """maps.txt is optional; without it an unknown map name is not reported."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text(_area(entrance_0="On,345,230,No Such Map,-1,-1,0"), encoding="utf-8")
    assert city.find_problems(city_txt) == []


def test_main_reports_missing_maps_file(tmp_path: Path, fixtures_dir: Path) -> None:
    """A --maps path that does not exist is reported rather than silently skipping the check."""
    assert city.main([str(fixtures_dir / "city.txt"), "--maps", str(tmp_path / "nope.txt")]) is True


def test_main_missing_file(tmp_path: Path) -> None:
    """A missing city.txt is reported rather than raising."""
    assert city.main([str(tmp_path / "nonexistent.txt")]) is True
