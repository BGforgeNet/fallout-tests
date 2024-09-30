#!/bin/bash

set -xeu -o pipefail

sudo apt-get install -y -qq -o=Dpkg::Use-Pty=0 virtualenv

echo "VIRTUALENV_PATH=${GITHUB_ACTION_PATH}/venv" >>"$GITHUB_ENV" # Next steps
export VIRTUALENV_PATH="${GITHUB_ACTION_PATH}/venv"               # This step
virtualenv "$VIRTUALENV_PATH"
# shellcheck source=/dev/null   # Nothing interesting here
source "$VIRTUALENV_PATH/bin/activate" >/dev/null 2>&1 || true # Very verbose
pip3 install -r "$GITHUB_ACTION_PATH/requirements.txt" --quiet
echo "${GITHUB_ACTION_PATH}/scripts" >>"$GITHUB_PATH"
