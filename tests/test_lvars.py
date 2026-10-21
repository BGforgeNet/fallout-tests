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

    assert lvars.main([str(tmp_path), str(lst_file)]) is True


REACTION_HEADER = """\
#define LVAR_reaction                   (0)             // Holds reaction number value.
#define LVAR_reaction_level             (1)
#define LVAR_got_reaction               (2)
#define LVAR_base_reaction              (3)
#define good_critter_reaction           (local_var(LVAR_reaction_level) >= 3)
#define ReactToLevel                    if (good_critter_reaction) then \\
                                            set_local_var(LVAR_got_reaction, 1)
procedure react_check begin
   ReactToLevel;
end
#define unrelated_macro                 (1)
"""


def write_tree(root: Path, script: str, extra: dict[str, str] | None = None) -> Path:
    """Write a scripts tree with a reaction header, one script and optional extra files; return scripts.lst."""
    (root / "headers").mkdir(parents=True)
    (root / "headers" / "modreact.h").write_text(REACTION_HEADER, encoding="utf-8")
    (root / "town").mkdir()
    (root / "town" / "tccritr.ssl").write_text(script, encoding="utf-8")
    for rel, text in (extra or {}).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    lst_file = root / "scripts.lst"
    lst_file.write_text("tccritr.int    local_vars=10\n", encoding="utf-8")
    return lst_file


def test_get_reaction_names_follows_macros_and_procedures(tmp_path: Path) -> None:
    """Macros and header procedures reaching the reaction LVARs, directly or through each other, are found."""
    header = tmp_path / "modreact.h"
    header.write_text(REACTION_HEADER, encoding="utf-8")
    names = lvars.get_reaction_names([header])
    assert names == lvars.REACTION_LVARS | {"good_critter_reaction", "ReactToLevel", "react_check"}


def test_strip_comments_keeps_strings_and_lines() -> None:
    """Comments become whitespace, string literals holding comment markers stay, and the line count is kept."""
    assert lvars.strip_comments('a // gone\n"http://x" /* gone\n*/ b') == 'a  \n"http://x" \n b'


def test_reaction_clash_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A script using a reaction macro while defining its own LVAR on 0-3 fails, naming the LVAR."""
    lst_file = write_tree(tmp_path, "#define LVAR_Flags (1)\nprocedure talk_p_proc begin\n   ReactToLevel;\nend\n")
    assert lvars.main([str(tmp_path), str(lst_file)]) is True
    assert capsys.readouterr().out == (
        "Script tccritr uses the reaction LVARs, which modreact.h keeps at indices 0-3, but defines LVAR_Flags as 1.\n"
    )


def test_reaction_clash_through_header_procedure(tmp_path: Path) -> None:
    """Calling a header procedure that reaches the reaction LVARs counts as using them."""
    lst_file = write_tree(tmp_path, "#define LVAR_Flags (0)\nprocedure talk_p_proc begin\n   call react_check;\nend\n")
    assert lvars.main([str(tmp_path), str(lst_file)]) is True


def test_reaction_clash_from_included_script(tmp_path: Path) -> None:
    """LVARs defined in an included .ssl file count as the including script's."""
    lst_file = write_tree(
        tmp_path,
        '#include "../template/tpl.ssl"\nprocedure talk_p_proc begin\n   ReactToLevel;\nend\n',
        {"template/tpl.ssl": "#define LVAR_Tpl_State (2)\n"},
    )
    assert lvars.main([str(tmp_path), str(lst_file)]) is True


@pytest.mark.parametrize(
    "script",
    [
        pytest.param("#define LVAR_Flags (0)\nprocedure start begin\nend\n", id="no-reaction-use"),
        pytest.param("#define LVAR_Flags (0)\n// ReactToLevel;\n/* ReactToLevel; */\n", id="use-commented-out"),
        pytest.param("#define LVAR_Herebefore (4)\nprocedure t begin\n   ReactToLevel;\nend\n", id="lvar-above-3"),
        pytest.param("#define LVAR_Flags (0)\nprocedure t begin\n   unrelated_macro;\nend\n", id="unrelated-macro"),
    ],
)
def test_reaction_no_clash(tmp_path: Path, script: str) -> None:
    """Scripts that do not use the reaction LVARs, or keep indices 0-3 free, pass."""
    lst_file = write_tree(tmp_path, script)
    assert lvars.main([str(tmp_path), str(lst_file)]) is False
