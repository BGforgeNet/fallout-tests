"""Tests for worldmap.py — validates worldmap encounter script combinations."""

from pathlib import Path

import pytest
import worldmap


def test_get_allowed_script_sets_none() -> None:
    """get_allowed_script_sets returns empty list when no sets provided."""
    result = worldmap.get_allowed_script_sets(None)
    assert result == []


def test_get_allowed_script_sets_single() -> None:
    """get_allowed_script_sets parses a single comma-separated set."""
    result = worldmap.get_allowed_script_sets(["100,101"])
    assert result == [[100, 101]]


def test_get_allowed_script_sets_sorted() -> None:
    """get_allowed_script_sets sorts script numbers within each set."""
    result = worldmap.get_allowed_script_sets(["201,200"])
    assert result == [[200, 201]]


def test_get_allowed_script_sets_inline_comments() -> None:
    """get_allowed_script_sets strips inline # and ; comments."""
    result = worldmap.get_allowed_script_sets(["100,101 # merchant guard", "201,200 ; caravan pair"])
    assert result == [[100, 101], [200, 201]]


def test_get_allowed_script_sets_rejects_non_numeric() -> None:
    """A -s value that is not a list of script numbers is named in the error."""
    with pytest.raises(ValueError, match="widget"):
        worldmap.get_allowed_script_sets(["100,widget"])


def test_main_reports_bad_script_set(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """main() reports an unparseable -s value and fails, rather than raising a bare ValueError."""
    wmap = tmp_path / "worldmap.txt"
    wmap.write_text("[Encounter: E01]\ntype_00=Pid:1, Script:100\n", encoding="utf-8")
    assert worldmap.main([str(wmap), "-s", "100,widget"]) is True
    assert "widget" in capsys.readouterr().out


def test_repeated_flag_keeps_every_set() -> None:
    """Regression: every -s occurrence contributes a set; none is silently dropped."""
    args = worldmap.parser.parse_args(["wmap.txt", "-s", "100,101", "-s", "200,201"])
    assert worldmap.get_allowed_script_sets(args.script_sets) == [[100, 101], [200, 201]]


def test_flag_before_positional_parses() -> None:
    """Regression: -s takes exactly one value, so it cannot swallow the worldmap path."""
    args = worldmap.parser.parse_args(["-s", "100,101", "wmap.txt"])
    assert args.worldmap == "wmap.txt"
    assert worldmap.get_allowed_script_sets(args.script_sets) == [[100, 101]]


def test_main_valid(fixtures_dir: Path) -> None:
    """main() exits cleanly for an encounter where all scripts match (same ID)."""
    # E01 has Script:100 and Script:100 — only one unique script, no combination to check
    worldmap.main([str(fixtures_dir / "worldmap.txt")])


def test_main_invalid(tmp_path: Path) -> None:
    """main() exits with code 1 when an encounter has an invalid script combination."""
    wmap = tmp_path / "worldmap.txt"
    wmap.write_text(
        "[Encounter: E01]\ntype_00=Pid:16777225, Script:100\ntype_01=Pid:16777226, Script:200\n",
        encoding="utf-8",
    )
    assert worldmap.main([str(wmap)]) is True


def test_main_invalid_allowed(tmp_path: Path) -> None:
    """main() exits cleanly when the combination is in the allowed set."""
    wmap = tmp_path / "worldmap.txt"
    wmap.write_text(
        "[Encounter: E01]\ntype_00=Pid:16777225, Script:100\ntype_01=Pid:16777226, Script:200\n",
        encoding="utf-8",
    )
    worldmap.main([str(wmap), "-s", "100,200"])


def test_missing_file(tmp_path: Path) -> None:
    """main() exits with code 1 for a nonexistent worldmap file."""
    assert worldmap.main([str(tmp_path / "nonexistent.txt")]) is True


def test_main_invalid_resolves_script_metadata(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """main() includes explicit scripts.h names and scripts.lst descriptions in invalid output."""
    wmap = tmp_path / "worldmap.txt"
    wmap.write_text(
        "\n[Encounter: E01]\ntype_00=Pid:16777225, Script:1\ntype_01=Pid:16777226, Script:2\n",
        encoding="utf-8",
    )

    scripts_h = tmp_path / "scripts.h"
    scripts_h.write_text(
        "#define SCRIPT_ALPHA (1)\n#define SCRIPT_BETA (2)\n",
        encoding="utf-8",
    )
    scripts_lst = tmp_path / "scripts.lst"
    scripts_lst.write_text(
        "alpha.int ; Alpha script\nbeta.int ; Beta script\n",
        encoding="utf-8",
    )

    assert worldmap.main([str(wmap), "--scripts-h", str(scripts_h), "--scripts-lst", str(scripts_lst)]) is True
    assert capsys.readouterr().out == (
        "Encounter: E01 (line 2) script combination is not allowed:\n"
        '  1 = SCRIPT_ALPHA = "Alpha script"\n'
        '  2 = SCRIPT_BETA = "Beta script"\n'
    )


@pytest.mark.integration
@pytest.mark.skip(
    reason=(
        "Needs a curated allowed-sets fixture: the pinned worldmap holds 26 multi-script encounter "
        "combinations, and deciding which are legitimate requires maintainer domain knowledge. "
        "Un-skip once those sets are recorded and passed via -s."
    )
)
def test_integration_worldmap(integration_repo: Path) -> None:
    """Integration: worldmap validation passes against Fallout2 Unofficial Patch data."""
    wmap_path = integration_repo / "data" / "data" / "worldmap.txt"
    assert worldmap.main([str(wmap_path)]) is False
