"""Tests for gam.py - counts .gam variables the way the engine does."""

from pathlib import Path

import gam


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "vars.gam"
    path.write_text(text, encoding="utf-8")
    return path


def test_count_vars_engine_rules(tmp_path: Path) -> None:
    """Empty lines and first-column // comments are skipped; any other line, even blank-looking, counts."""
    path = write(
        tmp_path,
        "MVAR_Before :=1;\n"  # before the section marker: not counted
        "MAP_GLOBAL_VARS:\n"
        "// a comment\n"
        "\n"
        "MVAR_A :=0;\n"
        "  // an indented comment still counts\n"
        "   \n"  # spaces only: counts too
        "MVAR_B :=0;\n",
    )
    expected_vars = 4  # MVAR_A, the indented comment, the spaces-only line, MVAR_B
    assert gam.count_vars(path, gam.MAP_SECTION) == expected_vars


def test_count_vars_crlf(tmp_path: Path) -> None:
    """CRLF files count like LF ones: the shipped .gam files all use CRLF."""
    path = tmp_path / "vars.gam"
    path.write_bytes(b"GAME_GLOBAL_VARS:\r\n\r\nGVAR_A :=0;\r\nGVAR_B :=0;\r\n")
    expected_vars = 2
    assert gam.count_vars(path, gam.GAME_SECTION) == expected_vars


def test_count_vars_no_section(tmp_path: Path) -> None:
    """A file without its section marker yields None."""
    assert gam.count_vars(write(tmp_path, "GVAR_A :=0;\n"), gam.GAME_SECTION) is None
