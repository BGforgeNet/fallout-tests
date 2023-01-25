#!/bin/bash

set -xeu -o pipefail

./scripts-lst.py "$INPUT_SCRIPTS_H" "$INPUT_SCRIPTS_LST"
./lvars.py "$INPUT_SCRIPTS_LST" "$INPUT_SCRIPTS_DIR"
./dialogs.py "$INPUT_DIALOG_DIR"
