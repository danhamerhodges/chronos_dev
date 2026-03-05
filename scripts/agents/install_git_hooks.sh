#!/usr/bin/env bash
set -euo pipefail

git config core.hooksPath .githooks
echo "Installed repo git hooks via core.hooksPath=.githooks"
