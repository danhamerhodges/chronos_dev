#!/usr/bin/env bash
set -euo pipefail

pnpm -C web test
pnpm -C web storybook:test
pytest tests/design_system tests/visual_regression -q
