"""Tests for mvars.py - validates map variable numbers against map .gam files."""

from pathlib import Path

import mvars
import pytest

GAM = "MAP_GLOBAL_VARS:\nMVAR_A :=0;\nMVAR_B :=0;\n"


def write_tree(root: Path, header: str, scripts: dict[str, str], gam: str = GAM) -> tuple[Path, Path]:
    """Write maps/town.gam, scripts/headers/town.h and scripts; return the maps and scripts directories."""
    maps_dir = root / "maps"
    scripts_dir = root / "scripts"
    (scripts_dir / "headers").mkdir(parents=True)
    maps_dir.mkdir()
    (maps_dir / "town.gam").write_text(gam, encoding="utf-8")
    (scripts_dir / "headers" / "town.h").write_text(header, encoding="utf-8")
    for name, text in scripts.items():
        (scripts_dir / f"{name}.ssl").write_text(text, encoding="utf-8")
    return maps_dir, scripts_dir


def test_used_out_of_range_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A used define at the .gam count is reported with its users."""
    maps_dir, scripts_dir = write_tree(
        tmp_path,
        "#define MVAR_A (0)\n#define MVAR_C (2)\n",
        {"tcguard": "procedure p begin dec_map_var(MVAR_C); end\n", "tcother": "x := MVAR_C;\n"},
    )
    assert mvars.main([str(maps_dir), str(scripts_dir)]) is True
    assert capsys.readouterr().out == (
        "town.h defines MVAR_C as 2, but town.gam declares 2 map variables; used by tcguard, tcother.\n"
    )


@pytest.mark.parametrize(
    ("header", "script"),
    [
        pytest.param("#define MVAR_B (1)\n", "x := MVAR_B;\n", id="in-range"),
        pytest.param("#define MVAR_C (2)\n", "x := 1;\n", id="unused"),
        pytest.param("#define MVAR_C (2)\n", "// x := MVAR_C;\n/* MVAR_C */\n", id="used-only-in-comments"),
        pytest.param("/*#define MVAR_C (2)*/\n", "x := MVAR_C;\n", id="define-commented-out"),
    ],
)
def test_no_problem(tmp_path: Path, header: str, script: str) -> None:
    """In-range, unused, comment-only and commented-out cases pass."""
    maps_dir, scripts_dir = write_tree(tmp_path, header, {"tcguard": script})
    assert mvars.main([str(maps_dir), str(scripts_dir)]) is False


def test_gam_without_section_has_no_vars(tmp_path: Path) -> None:
    """Without the section marker the engine reads no variables, so even index 0 is out of range."""
    maps_dir, scripts_dir = write_tree(
        tmp_path, "#define MVAR_A (0)\n", {"tcguard": "x := MVAR_A;\n"}, gam="MVAR_A :=0;\n"
    )
    assert mvars.main([str(maps_dir), str(scripts_dir)]) is True


def test_gam_without_header_skipped(tmp_path: Path) -> None:
    """A .gam with no matching header has nothing to check."""
    maps_dir, scripts_dir = write_tree(tmp_path, "#define MVAR_C (5)\n", {"tcguard": "x := MVAR_C;\n"})
    (scripts_dir / "headers" / "town.h").rename(scripts_dir / "headers" / "other.h")
    assert mvars.main([str(maps_dir), str(scripts_dir)]) is False


def test_missing_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A missing directory is named and fails the check."""
    assert mvars.main([str(tmp_path / "nope"), str(tmp_path)]) is True
    assert capsys.readouterr().out == f"{tmp_path / 'nope'} is not a directory.\n"


def test_fixture_tree_passes(fixtures_dir: Path) -> None:
    """The checked-in fixtures, with an unused out-of-range define, pass."""
    assert mvars.main([str(fixtures_dir / "maps"), str(fixtures_dir)]) is False
