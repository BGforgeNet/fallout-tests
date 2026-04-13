"""Tests for lvars.py — validates local variable allocations in Fallout scripts."""

from pathlib import Path

import lvars
import pytest


def test_get_lvars_map(fixtures_dir: Path) -> None:
    """get_lvars_map parses local_vars entries from scripts.lst correctly."""
    result = lvars.get_lvars_map(fixtures_dir / "scripts_lvars.lst")
    assert result == {"vcdoctor": 3, "vcmerch": 0}


def test_get_max_lvar(fixtures_dir: Path) -> None:
    """get_max_lvar returns the number of variables needed (max index + 1)."""
    result = lvars.get_max_lvar(fixtures_dir / "sample_lvars.ssl")
    # sample_lvars.ssl defines LVAR indices 0 and 1, so 2 variables are needed
    expected_var_count = 2  # max index (1) + 1
    assert result == expected_var_count


def test_get_max_lvar_no_lvars(fixtures_dir: Path) -> None:
    """get_max_lvar returns 0 when a script has no LVAR defines."""
    # sample.ssl has no LVAR defines
    result = lvars.get_max_lvar(fixtures_dir / "sample.ssl")
    assert result == 0


def test_main_passing(tmp_path: Path) -> None:
    """main() exits cleanly when allocations are sufficient."""
    ssl_file = tmp_path / "vcdoctor.ssl"
    ssl_file.write_text(
        "#define LVAR_Status   (0)\n#define LVAR_Counter  (1)\n",
        encoding="utf-8",
    )
    lst_file = tmp_path / "scripts.lst"
    # Allocate 3 vars; script needs 2 — should pass
    lst_file.write_text("vcdoctor.int    local_vars=3\n", encoding="utf-8")

    lvars.main([str(tmp_path), str(lst_file)])


def test_main_failing(tmp_path: Path) -> None:
    """main() exits with code 1 when allocation is insufficient."""
    ssl_file = tmp_path / "vcdoctor.ssl"
    ssl_file.write_text(
        "#define LVAR_Status   (0)\n#define LVAR_Counter  (1)\n#define LVAR_Extra    (2)\n",
        encoding="utf-8",
    )
    lst_file = tmp_path / "scripts.lst"
    # Allocate only 2 vars; script needs 3 — should fail
    lst_file.write_text("vcdoctor.int    local_vars=2\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        lvars.main([str(tmp_path), str(lst_file)])
    assert exc_info.value.code == 1


@pytest.mark.integration
def test_integration_lvars(integration_repo: Path) -> None:
    """Integration: lvars validation passes against Fallout2 Unofficial Patch data."""
    scripts_dir = integration_repo / "scripts_src"
    scripts_lst_path = integration_repo / "data" / "scripts" / "scripts.lst"
    if scripts_dir.exists() and scripts_lst_path.exists():
        lvars.main([str(scripts_dir), str(scripts_lst_path)])
