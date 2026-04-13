"""Tests for action.py — GitHub Action dispatcher and env var defaults."""

import os
from pathlib import Path
from unittest.mock import patch

import action
import pytest


def test_parse_script_sets_empty() -> None:
    """parse_script_sets returns empty list for empty string."""
    assert action.parse_script_sets("") == []


def test_parse_script_sets_single() -> None:
    """parse_script_sets converts a single space-separated line to comma-separated."""
    assert action.parse_script_sets("100 101") == ["100,101"]


def test_parse_script_sets_multiline() -> None:
    """parse_script_sets handles multiple lines producing multiple sets."""
    result = action.parse_script_sets("100 101\n200 201 202")
    assert result == ["100,101", "200,201,202"]


def test_parse_script_sets_blank_lines() -> None:
    """parse_script_sets skips blank lines."""
    result = action.parse_script_sets("100 101\n\n200 201")
    assert result == ["100,101", "200,201"]


def test_parse_script_sets_inline_comments() -> None:
    """parse_script_sets strips inline # and ; comments."""
    result = action.parse_script_sets("100 101 # merchant guard\n200 201 ; caravan pair")
    assert result == ["100,101", "200,201"]


def test_main_defaults_no_run() -> None:
    """Regression: main() uses os.environ.get() defaults and does not crash when INPUT_* vars are absent.

    All checks are disabled via env so no actual file I/O is attempted.
    """
    env_override = {
        "INPUT_CHECK_SCRIPTS": "false",
        "INPUT_CHECK_LVARS": "false",
        "INPUT_CHECK_MSGS": "false",
        "INPUT_WORLDMAP_PATH": "",
    }
    # Remove any INPUT_* vars that may be set and replace with the override
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("INPUT_")}
    clean_env.update(env_override)
    with patch.dict(os.environ, clean_env, clear=True):
        action.main()  # Must not raise KeyError when INPUT_* vars are absent


def test_main_defaults_values() -> None:
    """main() does not raise KeyError for any INPUT_* variable when all are absent from environment.

    Verifies that every os.environ.get() call has a default (fix 3 regression guard).
    """
    # Patch each validator's main to a no-op so we only test that defaults are reached
    with (
        patch("scripts_lst.main") as mock_scripts,
        patch("lvars.main") as mock_lvars,
        patch("dialogs.main") as mock_dialogs,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "true",
                "INPUT_CHECK_LVARS": "true",
                "INPUT_CHECK_MSGS": "true",
                "INPUT_WORLDMAP_PATH": "",
            },
            clear=True,
        ),
    ):
        action.main()
        mock_scripts.assert_called_once_with(["scripts_src/headers/scripts.h", "data/scripts/scripts.lst"])
        mock_lvars.assert_called_once_with(["scripts_src", "data/scripts/scripts.lst"])
        mock_dialogs.assert_called_once_with(["data/text/english/dialog", "scripts_src"])


def test_main_worldmap_path(tmp_path: Path) -> None:
    """main() invokes worldmap.main() when INPUT_WORLDMAP_PATH is set."""
    wmap = tmp_path / "worldmap.txt"
    scripts_h = tmp_path / "scripts.h"
    scripts_lst = tmp_path / "scripts.lst"
    wmap.write_text("[Encounter: E01]\ntype_00=Pid:16777225, Script:100\n", encoding="utf-8")
    scripts_h.write_text("#define SCRIPT_ALPHA (100)\n", encoding="utf-8")
    scripts_lst.write_text("alpha.int ; Alpha script\n", encoding="utf-8")
    with (
        patch("worldmap.main") as mock_worldmap,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "false",
                "INPUT_CHECK_LVARS": "false",
                "INPUT_CHECK_MSGS": "false",
                "INPUT_WORLDMAP_PATH": str(wmap),
                "INPUT_SCRIPTS_H": str(scripts_h),
                "INPUT_SCRIPTS_LST": str(scripts_lst),
                "INPUT_WORLDMAP_SCRIPT_SETS": "",
            },
            clear=True,
        ),
    ):
        action.main()
        mock_worldmap.assert_called_once_with(
            [str(wmap), "--scripts-h", str(scripts_h), "--scripts-lst", str(scripts_lst)]
        )


def test_main_worldmap_with_sets(tmp_path: Path) -> None:
    """main() passes parsed script sets to worldmap.main() when INPUT_WORLDMAP_SCRIPT_SETS is set."""
    wmap = tmp_path / "worldmap.txt"
    scripts_h = tmp_path / "scripts.h"
    scripts_lst = tmp_path / "scripts.lst"
    wmap.write_text("[Encounter: E01]\ntype_00=Pid:16777225, Script:100\n", encoding="utf-8")
    scripts_h.write_text("#define SCRIPT_ALPHA (100)\n", encoding="utf-8")
    scripts_lst.write_text("alpha.int ; Alpha script\n", encoding="utf-8")
    with (
        patch("worldmap.main") as mock_worldmap,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "false",
                "INPUT_CHECK_LVARS": "false",
                "INPUT_CHECK_MSGS": "false",
                "INPUT_WORLDMAP_PATH": str(wmap),
                "INPUT_SCRIPTS_H": str(scripts_h),
                "INPUT_SCRIPTS_LST": str(scripts_lst),
                "INPUT_WORLDMAP_SCRIPT_SETS": "100 200",
            },
            clear=True,
        ),
    ):
        action.main()
        mock_worldmap.assert_called_once_with(
            [str(wmap), "--scripts-h", str(scripts_h), "--scripts-lst", str(scripts_lst), "-s", "100,200"]
        )


@pytest.mark.integration
def test_integration_action(integration_repo: Path) -> None:
    """Integration: action.main() passes against Fallout2 Unofficial Patch data."""
    env = {
        "INPUT_CHECK_SCRIPTS": "true",
        "INPUT_CHECK_LVARS": "true",
        "INPUT_CHECK_MSGS": "true",
        "INPUT_SCRIPTS_H": str(integration_repo / "scripts_src" / "headers" / "scripts.h"),
        "INPUT_SCRIPTS_LST": str(integration_repo / "data" / "scripts" / "scripts.lst"),
        "INPUT_SCRIPTS_DIR": str(integration_repo / "scripts_src"),
        "INPUT_DIALOG_DIR": str(integration_repo / "data" / "text" / "english" / "dialog"),
        "INPUT_WORLDMAP_PATH": "",
    }
    with patch.dict(os.environ, env, clear=True):
        action.main()
