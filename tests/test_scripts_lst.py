"""Tests for scripts_lst.py — validates scripts.h / scripts.lst consistency."""

from pathlib import Path

import pytest
import scripts_lst


def test_parse_h(fixtures_dir: Path) -> None:
    """parse_h returns correct by-number and by-name dicts from a valid scripts.h."""
    h_by_num, h_by_name = scripts_lst.parse_h(fixtures_dir / "scripts.h")
    assert h_by_num == {1: "VCDOCTOR", 2: "VCMERCH", 3: "VCGUARD"}
    assert h_by_name == {"VCDOCTOR": 1, "VCMERCH": 2, "VCGUARD": 3}


def test_parse_lst(fixtures_dir: Path) -> None:
    """parse_lst returns 1-based line-number keys mapping to uppercase script names."""
    lst_by_num = scripts_lst.parse_lst(fixtures_dir / "scripts.lst")
    assert lst_by_num == {1: "VCDOCTOR", 2: "VCMERCH", 3: "VCGUARD"}


def test_check_lst_dupes_no_dupes(fixtures_dir: Path) -> None:
    """check_lst_dupes returns False when no duplicates are present."""
    lst_by_num = scripts_lst.parse_lst(fixtures_dir / "scripts.lst")
    assert scripts_lst.check_lst_dupes(lst_by_num) is False


def test_check_lst_dupes(tmp_path: Path) -> None:
    """check_lst_dupes detects duplicate script names."""
    lst_file = tmp_path / "scripts.lst"
    lst_file.write_text("vcdoctor.int\nvcmerch.int\nvcdoctor.int\n", encoding="utf-8")
    lst_by_num = scripts_lst.parse_lst(lst_file)
    assert scripts_lst.check_lst_dupes(lst_by_num) is True


def test_check_lst_dupes_reserved(tmp_path: Path) -> None:
    """RESERVED entries are not flagged as duplicates even when repeated."""
    lst_file = tmp_path / "scripts.lst"
    lst_file.write_text("RESERVED\nvcmerch.int\nRESERVED\n", encoding="utf-8")
    lst_by_num = scripts_lst.parse_lst(lst_file)
    assert scripts_lst.check_lst_dupes(lst_by_num) is False


def test_last_line_checked(tmp_path: Path) -> None:
    """Regression: the script on the final line is checked against scripts.h (off-by-one fix)."""
    # scripts.h defines 3 scripts: numbers 0, 1, 2
    # scripts.lst has 3 entries; line 3 (VCGUARD) is the last and must be validated
    h_file = tmp_path / "scripts.h"
    # Use 1-based numbers matching scripts.lst line positions
    h_file.write_text(
        "#define SCRIPT_VCDOCTOR    (1)\n#define SCRIPT_VCMERCH     (2)\n#define SCRIPT_VCGUARD     (3)\n",
        encoding="utf-8",
    )
    lst_file = tmp_path / "scripts.lst"
    # Introduce a mismatch on the last line (VCGUARD → WRONG)
    lst_file.write_text("vcdoctor.int\nvcmerch.int\nwrong.int\n", encoding="utf-8")

    h_by_num, h_by_name = scripts_lst.parse_h(h_file)
    lst_by_num = scripts_lst.parse_lst(lst_file)
    # Before the fix, range(1, 3) skipped line 3, so the mismatch was invisible
    result = scripts_lst.check_scripts_h(lst_by_num, h_by_num, h_by_name)
    assert result is True, "Last-line mismatch must be detected"


def test_main_passing(fixtures_dir: Path) -> None:
    """main() exits cleanly when scripts.h and scripts.lst are consistent."""
    scripts_lst.main([str(fixtures_dir / "scripts.h"), str(fixtures_dir / "scripts.lst")])


def test_main_failing(tmp_path: Path) -> None:
    """main() exits with code 1 when there is a mismatch."""
    h_file = tmp_path / "scripts.h"
    # scripts.h defines VCDOCTOR at position 1, but scripts.lst line 1 is 'wrong'
    h_file.write_text("#define SCRIPT_VCDOCTOR    (1)\n", encoding="utf-8")
    lst_file = tmp_path / "scripts.lst"
    lst_file.write_text("wrong.int\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        scripts_lst.main([str(h_file), str(lst_file)])
    assert exc_info.value.code == 1
