#!/bin/bash

set -xeu -o pipefail

echo "${GITHUB_ACTION_PATH}/scripts" >>"$GITHUB_PATH"
