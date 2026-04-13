"""Tests for dialogs.py — validates dialog message references in Fallout scripts."""

from pathlib import Path

import dialogs
import pytest


def test_get_generic_messages(fixtures_dir: Path) -> None:
    """get_generic_messages parses message IDs from a valid generic.msg file."""
    result = dialogs.get_generic_messages(fixtures_dir / "generic.msg")
    assert result is not None
    assert "100" in result
    assert "200" in result


def test_get_generic_messages_missing(tmp_path: Path) -> None:
    """Regression: get_generic_messages returns None when file does not exist."""
    result = dialogs.get_generic_messages(tmp_path / "nonexistent.msg")
    assert result is None


def test_get_script_messages_display_mstr() -> None:
    """get_script_messages extracts IDs from display_mstr calls."""
    result = dialogs.get_script_messages("   display_mstr(100)")
    assert "100" in result


def test_get_script_messages_range() -> None:
    """get_script_messages expands floater_rand ranges into individual IDs."""
    result = dialogs.get_script_messages("   floater_rand(100, 103)")
    assert result == ["100", "101", "102", "103"]


def test_get_script_messages_empty_line() -> None:
    """get_script_messages returns empty list for lines with no message calls."""
    result = dialogs.get_script_messages("// this is a comment")
    assert result == []


def test_main_passing(tmp_path: Path, fixtures_dir: Path) -> None:
    """main() exits cleanly when all referenced messages exist in dialog files."""
    dialog_dir = tmp_path / "dialog"
    dialog_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    # Copy generic.msg into dialog dir
    (dialog_dir / "generic.msg").write_bytes((fixtures_dir / "generic.msg").read_bytes())

    # Script references message IDs that exist in its .msg file
    (scripts_dir / "vcdoctor.ssl").write_text(
        "#define NAME    SCRIPT_VCDOCTOR\n   display_mstr(100)\n",
        encoding="utf-8",
    )
    (dialog_dir / "vcdoctor.msg").write_bytes(b"{100}{}{Hello.}\n")

    dialogs.main([str(dialog_dir), str(scripts_dir)])


def test_main_failing(tmp_path: Path) -> None:
    """main() exits with code 1 when a script references a missing message ID."""
    dialog_dir = tmp_path / "dialog"
    dialog_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    # No generic.msg — missing file should be handled gracefully (returns None → treated as empty)
    (scripts_dir / "vcdoctor.ssl").write_text(
        "#define NAME    SCRIPT_VCDOCTOR\n   display_mstr(999)\n",
        encoding="utf-8",
    )
    # dialog file exists but is missing the referenced ID
    (dialog_dir / "vcdoctor.msg").write_bytes(b"{100}{}{Hello.}\n")

    with pytest.raises(SystemExit) as exc_info:
        dialogs.main([str(dialog_dir), str(scripts_dir)])
    assert exc_info.value.code == 1


def test_main_missing_generic_msg(tmp_path: Path) -> None:
    """Regression: main() does not crash when generic.msg is absent."""
    dialog_dir = tmp_path / "dialog"
    dialog_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()

    # No generic.msg in dialog_dir — should not raise an exception
    (scripts_dir / "vcdoctor.ssl").write_text(
        "#define NAME    SCRIPT_VCDOCTOR\n   display_mstr(100)\n",
        encoding="utf-8",
    )
    (dialog_dir / "vcdoctor.msg").write_bytes(b"{100}{}{Hello.}\n")

    # Should not raise — generic.msg absence is handled gracefully
    dialogs.main([str(dialog_dir), str(scripts_dir)])
