#!/usr/bin/env bash
set -euo pipefail

REQ_ID="${1:-}"
ROOT_DIR="${2:-$(pwd)}"

if [[ -z "$REQ_ID" ]]; then
  echo "usage: $0 <REQ-ID> [repo-root]"
  echo "example: $0 ENG-002 /Users/geekboy/Projects/chronos_dev"
  exit 1
fi

if [[ ! "$REQ_ID" =~ ^(FR|ENG|SEC|OPS|NFR|DS)-[0-9]{3}$ ]]; then
  echo "invalid requirement id: $REQ_ID"
  echo "expected format: FR-001, ENG-002, SEC-013, OPS-004, NFR-010, DS-007"
  exit 1
fi

cd "$ROOT_DIR"

case "$REQ_ID" in
  FR-*)  CANON_DOC="docs/specs/chronosrefine_functional_requirements.md" ;;
  ENG-*) CANON_DOC="docs/specs/chronosrefine_engineering_requirements.md" ;;
  SEC-*|OPS-*) CANON_DOC="docs/specs/chronosrefine_security_operations_requirements.md" ;;
  NFR-*) CANON_DOC="docs/specs/chronosrefine_nonfunctional_requirements.md" ;;
  DS-*)  CANON_DOC="docs/specs/chronosrefine_design_requirements.md" ;;
  *)     CANON_DOC="" ;;
esac

echo "== Requirement Planner Discovery =="
echo "req_id: $REQ_ID"
echo "root: $ROOT_DIR"
echo "canonical_doc: $CANON_DOC"

echo

echo "-- Canonical requirement section --"
rg -n "^### ${REQ_ID}:" "$CANON_DOC" || echo "not found in canonical doc"

echo

echo "-- Coverage matrix hits --"
rg -n "\*\*${REQ_ID}\*\*|^## Phase [1-6]:" "docs/specs/ChronosRefine Requirements Coverage Matrix.md" || true

echo

echo "-- Implementation plan hits --"
rg -n "${REQ_ID}|^### Phase [1-6]:|\*\*Requirements Implemented:\*\*" "docs/specs/chronosrefine_implementation_plan.md" || true

echo

echo "-- Test template / test references --"
rg -n "${REQ_ID}|Maps to:" "docs/specs/chronosrefine_test_templates.md" || true

echo
echo "discovery complete"
