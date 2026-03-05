#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$(pwd)}"
cd "$ROOT_DIR"

echo "== ChronosRefine Spec Consistency Audit =="
echo "root: $ROOT_DIR"

echo

echo "-- Canonical files present --"
required=(
  "docs/specs/chronosrefine_functional_requirements.md"
  "docs/specs/chronosrefine_engineering_requirements.md"
  "docs/specs/chronosrefine_security_operations_requirements.md"
  "docs/specs/chronosrefine_nonfunctional_requirements.md"
  "docs/specs/chronosrefine_design_requirements.md"
  "docs/specs/ChronosRefine Requirements Coverage Matrix.md"
  "docs/specs/chronosrefine_implementation_plan.md"
  "docs/specs/chronosrefine_test_templates.md"
)

missing=0
for file in "${required[@]}"; do
  if [[ -f "$file" ]]; then
    echo "OK  $file"
  else
    echo "MISS $file"
    missing=1
  fi
done

echo

echo "-- Stale reference scan --"
rg -n "chronosrefine_prd_final|coverage_matrix\\.md|\\bagents\\.md\\b" docs/specs || true

echo

echo "-- Coverage matrix phases --"
rg -n "^## Phase [1-6]:" "docs/specs/ChronosRefine Requirements Coverage Matrix.md" || true

echo

echo "-- Implementation plan phase declarations --"
rg -n "^### Phase [1-6]:|\*\*Requirements Implemented:\*\*" "docs/specs/chronosrefine_implementation_plan.md" || true

echo

echo "-- Implementation plan requirement counts --"
rg -n "\([0-9]+ requirements\)" "docs/specs/chronosrefine_implementation_plan.md" || true

if [[ "$missing" -ne 0 ]]; then
  echo
  echo "RESULT: FAIL (missing canonical files)"
  exit 2
fi

echo
echo "RESULT: PASS (manual review required for any reported findings)"
