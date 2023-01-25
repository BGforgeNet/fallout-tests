#!/bin/bash

set -xeu -o pipefail

if [[ "$INPUT_CHECK_SCRIPTS" == "true" ]]; then
    ./scripts/scripts_lst.py "$INPUT_SCRIPTS_H" "$INPUT_SCRIPTS_LST"
fi
if [[ "$INPUT_CHECK_LVARS" == "true" ]]; then
    ./scripts/lvars.py "$INPUT_SCRIPTS_LST" "$INPUT_SCRIPTS_DIR"
fi
if [[ "$INPUT_CHECK_MSGS" == "true" ]]; then
    ./scripts/dialogs.py "$INPUT_DIALOG_DIR" "$INPUT_SCRIPTS_DIR"
fi
