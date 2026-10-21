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


def test_parse_script_sets_accepts_comma_separated_line() -> None:
    """A comma-separated line is one set, matching how -s spells it on the CLI."""
    assert action.parse_script_sets("100,101") == ["100,101"]


def test_parse_script_sets_rejects_mixed_separators() -> None:
    """Regression: a line mixing commas and spaces used to merge two sets into one silently."""
    with pytest.raises(ValueError, match="100,101 200,201"):
        action.parse_script_sets("100,101 200,201")


def test_parse_script_sets_rejects_non_numeric() -> None:
    """A set entry that is not a script number is reported rather than passed downstream."""
    with pytest.raises(ValueError, match="widget"):
        action.parse_script_sets("100 widget")


def test_main_reports_bad_script_sets_without_running_worldmap(tmp_path: Path) -> None:
    """An unparseable script set fails the run with a message instead of a traceback."""
    wmap = tmp_path / "worldmap.txt"
    wmap.write_text("[Encounter: E01]\ntype_00=Pid:1, Script:100\n", encoding="utf-8")
    with (
        patch("worldmap.main") as mock_worldmap,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "false",
                "INPUT_CHECK_LVARS": "false",
                "INPUT_CHECK_MSGS": "false",
                "INPUT_WORLDMAP_PATH": str(wmap),
                "INPUT_SCRIPTS_H": "",
                "INPUT_SCRIPTS_LST": "",
                "INPUT_WORLDMAP_SCRIPT_SETS": "100,101 200,201",
            },
            clear=True,
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        action.main()
    assert exc_info.value.code == 1
    mock_worldmap.assert_not_called()


def test_parse_script_sets_inline_comments() -> None:
    """parse_script_sets strips inline # and ; comments."""
    result = action.parse_script_sets("100 101 # merchant guard\n200 201 ; caravan pair")
    assert result == ["100,101", "200,201"]


@pytest.mark.parametrize("value", ["", "false", "FALSE", " false ", "no", "off"])
def test_is_disabled_accepts_boolean_looking_values(value: str) -> None:
    """A YAML `false` reaches the action as the truthy string "false"; it must still mean "skip"."""
    assert action.is_disabled(value) is True


@pytest.mark.parametrize("value", ["data/data/worldmap.txt", "false.txt", "0"])
def test_is_disabled_treats_real_paths_as_enabled(value: str) -> None:
    """Anything that could name a file is a path, not an off-switch."""
    assert action.is_disabled(value) is False


def test_main_city_path(tmp_path: Path) -> None:
    """main() invokes city.main() when INPUT_CITY_PATH is set."""
    city_txt = tmp_path / "city.txt"
    city_txt.write_text("[Area 00]\n", encoding="utf-8")
    with (
        patch("city.main", return_value=False) as mock_city,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "false",
                "INPUT_CHECK_LVARS": "false",
                "INPUT_CHECK_MSGS": "false",
                "INPUT_CITY_PATH": str(city_txt),
                "INPUT_WORLDMAP_PATH": "",
            },
            clear=True,
        ),
    ):
        action.main()
        mock_city.assert_called_once_with([str(city_txt)])


def test_main_maps_path(tmp_path: Path) -> None:
    """main() invokes maps.main() when INPUT_MAPS_PATH is set."""
    maps_txt = tmp_path / "maps.txt"
    maps_txt.write_text("[Map 000]\n", encoding="utf-8")
    with (
        patch("maps.main", return_value=False) as mock_maps,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "false",
                "INPUT_CHECK_LVARS": "false",
                "INPUT_CHECK_MSGS": "false",
                "INPUT_MAPS_PATH": str(maps_txt),
                "INPUT_WORLDMAP_PATH": "",
            },
            clear=True,
        ),
    ):
        action.main()
        mock_maps.assert_called_once_with([str(maps_txt)])


def test_main_skips_maps_when_unset() -> None:
    """maps.txt is optional, so an unset path skips the check rather than failing."""
    with (
        patch("maps.main") as mock_maps,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "false",
                "INPUT_CHECK_LVARS": "false",
                "INPUT_CHECK_MSGS": "false",
                "INPUT_WORLDMAP_PATH": "",
            },
            clear=True,
        ),
    ):
        action.main()
        mock_maps.assert_not_called()


def test_main_skips_city_when_unset() -> None:
    """city.txt is optional, so an unset path skips the check rather than failing."""
    with (
        patch("city.main") as mock_city,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "false",
                "INPUT_CHECK_LVARS": "false",
                "INPUT_CHECK_MSGS": "false",
                "INPUT_WORLDMAP_PATH": "",
            },
            clear=True,
        ),
    ):
        action.main()
        mock_city.assert_not_called()


def test_main_skips_worldmap_when_disabled_by_literal_false() -> None:
    """Regression: worldmap_path: false skips the check instead of looking for a file named "false"."""
    with (
        patch("worldmap.main") as mock_worldmap,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "false",
                "INPUT_CHECK_LVARS": "false",
                "INPUT_CHECK_MSGS": "false",
                "INPUT_WORLDMAP_PATH": "false",
            },
            clear=True,
        ),
    ):
        action.main()
        mock_worldmap.assert_not_called()


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
        patch("scripts_lst.main", return_value=False) as mock_scripts,
        patch("lvars.main", return_value=False) as mock_lvars,
        patch("dialogs.main", return_value=False) as mock_dialogs,
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
        patch("worldmap.main", return_value=False) as mock_worldmap,
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


OFF = {"INPUT_CHECK_SCRIPTS": "false", "INPUT_CHECK_LVARS": "false", "INPUT_CHECK_MSGS": "false"}


def test_main_quests_wiring() -> None:
    """quests.main() gets vault13.gam from beside quests.txt and the .msg files from game_msg_dir."""
    env = {**OFF, "INPUT_QUESTS_PATH": "mod/data/quests.txt", "INPUT_GAME_MSG_DIR": "mod/text/game"}
    with patch("quests.main", return_value=False) as mock_quests, patch.dict(os.environ, env, clear=True):
        action.main()
    mock_quests.assert_called_once_with(
        [
            "mod/data/quests.txt",
            "--quests-msg",
            str(Path("mod/text/game/quests.msg")),
            "--map-msg",
            str(Path("mod/text/game/map.msg")),
            "--gam",
            str(Path("mod/data/vault13.gam")),
        ]
    )


def test_main_quests_default_game_dir() -> None:
    """Without game_msg_dir, the .msg files come from the English game directory, as action.yml declares."""
    env = {**OFF, "INPUT_QUESTS_PATH": "data/data/quests.txt"}
    with patch("quests.main", return_value=False) as mock_quests, patch.dict(os.environ, env, clear=True):
        action.main()
    assert mock_quests.call_args.args[0][2] == str(Path("data/text/english/game/quests.msg"))


def test_main_mvars_wiring() -> None:
    """mvars.main() gets the map .gam directory and the scripts directory."""
    env = {**OFF, "INPUT_MAP_GAM_DIR": "data/maps", "INPUT_SCRIPTS_DIR": "src"}
    with patch("mvars.main", return_value=False) as mock_mvars, patch.dict(os.environ, env, clear=True):
        action.main()
    mock_mvars.assert_called_once_with(["data/maps", "src"])


@pytest.mark.parametrize("value", ["", "false"])
def test_main_quests_and_mvars_off(value: str) -> None:
    """Empty or false path inputs skip the quests and map variable checks."""
    env = {**OFF, "INPUT_QUESTS_PATH": value, "INPUT_MAP_GAM_DIR": value}
    with (
        patch("quests.main", return_value=False) as mock_quests,
        patch("mvars.main", return_value=False) as mock_mvars,
        patch.dict(os.environ, env, clear=True),
    ):
        action.main()
    mock_quests.assert_not_called()
    mock_mvars.assert_not_called()


@pytest.mark.parametrize("failing", ["quests.main", "mvars.main"])
def test_main_new_checks_fail_the_run(failing: str) -> None:
    """A failing quests or map variable check fails the action."""
    env = {**OFF, "INPUT_QUESTS_PATH": "q.txt", "INPUT_MAP_GAM_DIR": "maps"}
    with (
        patch("quests.main", return_value=failing == "quests.main"),
        patch("mvars.main", return_value=failing == "mvars.main"),
        patch.dict(os.environ, env, clear=True),
        pytest.raises(SystemExit) as exc,
    ):
        action.main()
    assert exc.value.code == 1


def test_main_worldmap_with_sets(tmp_path: Path) -> None:
    """main() passes parsed script sets to worldmap.main() when INPUT_WORLDMAP_SCRIPT_SETS is set."""
    wmap = tmp_path / "worldmap.txt"
    scripts_h = tmp_path / "scripts.h"
    scripts_lst = tmp_path / "scripts.lst"
    wmap.write_text("[Encounter: E01]\ntype_00=Pid:16777225, Script:100\n", encoding="utf-8")
    scripts_h.write_text("#define SCRIPT_ALPHA (100)\n", encoding="utf-8")
    scripts_lst.write_text("alpha.int ; Alpha script\n", encoding="utf-8")
    with (
        patch("worldmap.main", return_value=False) as mock_worldmap,
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


def test_main_worldmap_emits_one_flag_per_set(tmp_path: Path) -> None:
    """Each parsed set gets its own -s flag, so no set is dropped downstream."""
    wmap = tmp_path / "worldmap.txt"
    wmap.write_text("[Encounter: E01]\ntype_00=Pid:16777225, Script:100\n", encoding="utf-8")
    with (
        patch("worldmap.main", return_value=False) as mock_worldmap,
        patch.dict(
            os.environ,
            {
                "INPUT_CHECK_SCRIPTS": "false",
                "INPUT_CHECK_LVARS": "false",
                "INPUT_CHECK_MSGS": "false",
                "INPUT_WORLDMAP_PATH": str(wmap),
                "INPUT_SCRIPTS_H": "",
                "INPUT_SCRIPTS_LST": "",
                "INPUT_WORLDMAP_SCRIPT_SETS": "100 101\n200 201 202",
            },
            clear=True,
        ),
    ):
        action.main()
        mock_worldmap.assert_called_once_with([str(wmap), "-s", "100,101", "-s", "200,201,202"])


def test_main_runs_every_validator_when_one_fails() -> None:
    """Regression: a failing validator no longer aborts the run, so one pass reports every category."""
    calls: list[str] = []

    def record(name: str, failed: bool):  # noqa: ANN202 - test helper
        def _run(argv: list[str]) -> bool:
            del argv
            calls.append(name)
            return failed

        return _run

    with (
        patch("scripts_lst.main", record("scripts_lst", True)),
        patch("lvars.main", record("lvars", True)),
        patch("dialogs.main", record("dialogs", False)),
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
        pytest.raises(SystemExit) as exc_info,
    ):
        action.main()
    assert calls == ["scripts_lst", "lvars", "dialogs"], "every validator must run despite earlier failures"
    assert exc_info.value.code == 1


def test_main_exits_zero_when_all_validators_pass() -> None:
    """main() exits 0 only when no validator reported a problem."""
    with (
        patch("scripts_lst.main", lambda argv: False),
        patch("lvars.main", lambda argv: False),
        patch("dialogs.main", lambda argv: False),
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
