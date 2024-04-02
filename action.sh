#!/bin/bash

set -xeu -o pipefail

if [[ "$INPUT_CHECK_SCRIPTS" == "true" ]]; then
    scripts_lst.py "$INPUT_SCRIPTS_H" "$INPUT_SCRIPTS_LST"
fi
if [[ "$INPUT_CHECK_LVARS" == "true" ]]; then
    lvars.py "$INPUT_SCRIPTS_DIR" "$INPUT_SCRIPTS_LST"
fi
if [[ "$INPUT_CHECK_MSGS" == "true" ]]; then
    dialogs.py "$INPUT_DIALOG_DIR" "$INPUT_SCRIPTS_DIR"
fi

if [[ "$INPUT_WORLDMAP_PATH" != "false" ]]; then
    sets_arg=""
    if [[ "$INPUT_WORLDMAP_SCRIPT_SETS" != "false" ]]; then
        sets_arg="-s $INPUT_WORLDMAP_SCRIPT_SETS"
    fi
    # we speficically want word splitting
    # shellcheck disable=SC2086
    worldmap.py "$INPUT_DIALOG_DIR" $sets_arg
fi
