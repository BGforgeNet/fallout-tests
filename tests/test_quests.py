"""Tests for quests.py - validates quests.txt against messages and global variables."""

from pathlib import Path

import pytest
import quests


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        pytest.param("1500, 100, 9, 2, 6", [1500, 100, 9, 2, 6], id="commas"),
        pytest.param("1500\t110 183,1 ,3", [1500, 110, 183, 1, 3], id="mixed-delimiters"),
        pytest.param("1500, 100, 9, 2, 6, 7", [1500, 100, 9, 2, 6], id="extra-field-ignored"),
        pytest.param("1500, 100, 9x, 2, 6", [1500, 100, 9, 2, 6], id="atoi-leading-digits"),
        pytest.param("# 1500, 100, 9, 2, 6", None, id="comment"),
        pytest.param("   # 1500, 100, 9, 2, 6", None, id="indented-comment"),
        pytest.param("1500, 100, 9, 2", None, id="too-few-fields"),
        pytest.param("", None, id="empty"),
    ],
)
def test_parse_fields(line: str, expected: list[int] | None) -> None:
    """Lines are split and skipped the way the engine's questInit does."""
    assert quests.parse_fields(line) == expected


def test_main_fixture_passes(fixtures_dir: Path) -> None:
    """The checked-in fixture set is consistent."""
    argv = [
        str(fixtures_dir / "quests.txt"),
        "--quests-msg",
        str(fixtures_dir / "quests.msg"),
        "--map-msg",
        str(fixtures_dir / "map.msg"),
        "--gam",
        str(fixtures_dir / "vault13.gam"),
    ]
    assert quests.main(argv) is False


def test_main_reports_each_problem(tmp_path: Path, fixtures_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing location, a missing description and an out-of-range gvar are each reported with their line."""
    quests_txt = tmp_path / "quests.txt"
    quests_txt.write_text("# header\n1501, 100, 1, 1, 2\n1500, 999, 3, 1, 2\n", encoding="utf-8")
    argv = [
        str(quests_txt),
        "--quests-msg",
        str(fixtures_dir / "quests.msg"),
        "--map-msg",
        str(fixtures_dir / "map.msg"),
        "--gam",
        str(fixtures_dir / "vault13.gam"),
    ]
    assert quests.main(argv) is True
    assert capsys.readouterr().out.splitlines() == [
        "quests.txt line 2: location 1501 is not in map.msg.",
        "quests.txt line 3: description 999 is not in quests.msg.",
        "quests.txt line 3: gvar 3 is outside vault13.gam, which declares 3.",
    ]


def test_main_missing_input(tmp_path: Path, fixtures_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing input file is named and fails the check."""
    missing = tmp_path / "nope.msg"
    argv = [
        str(fixtures_dir / "quests.txt"),
        "--quests-msg",
        str(missing),
        "--map-msg",
        str(fixtures_dir / "map.msg"),
        "--gam",
        str(fixtures_dir / "vault13.gam"),
    ]
    assert quests.main(argv) is True
    assert capsys.readouterr().out == f"{missing} does not exist.\n"


def test_main_gam_without_section(tmp_path: Path, fixtures_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A vault13.gam without its section marker is reported rather than read as zero variables."""
    bad_gam = tmp_path / "vault13.gam"
    bad_gam.write_text("GVAR_A :=0;\n", encoding="utf-8")
    argv = [
        str(fixtures_dir / "quests.txt"),
        "--quests-msg",
        str(fixtures_dir / "quests.msg"),
        "--map-msg",
        str(fixtures_dir / "map.msg"),
        "--gam",
        str(bad_gam),
    ]
    assert quests.main(argv) is True
    assert capsys.readouterr().out == f"{bad_gam} has no GAME_GLOBAL_VARS: section.\n"
