#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [ -z "${BUILD_SHA_OVERRIDE:-}" ]; then
  if [ -n "$(git status --porcelain)" ]; then
    echo "Refusing to stamp BUILD_SHA from a dirty worktree. Commit or stash changes before deploying." >&2
    exit 1
  fi
  BUILD_SHA="$(git rev-parse HEAD)"
else
  BUILD_SHA="${BUILD_SHA_OVERRIDE}"
fi

if ! printf '%s' "$BUILD_SHA" | grep -Eq '^[0-9a-f]{40}$'; then
  echo "BUILD_SHA must be a bare 40-character lowercase git commit SHA." >&2
  exit 1
fi

BUILD_TIME="${BUILD_TIME_OVERRIDE:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
if ! printf '%s' "$BUILD_TIME" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'; then
  echo "BUILD_TIME must be a UTC ISO-8601 timestamp with a trailing Z." >&2
  exit 1
fi

printf 'BUILD_SHA=%s\n' "$BUILD_SHA"
printf 'BUILD_TIME=%s\n' "$BUILD_TIME"
