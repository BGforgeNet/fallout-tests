#!/bin/bash

set -xeu -o pipefail

./scripts/scripts-lst.py "$INPUT_SCRIPTS_H" "$INPUT_SCRIPTS_LST"
./scripts/lvars.py "$INPUT_SCRIPTS_LST" "$INPUT_SCRIPTS_DIR"
./scripts/dialogs.py "$INPUT_DIALOG_DIR"
