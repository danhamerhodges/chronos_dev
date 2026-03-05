# Spec Consistency Audit Checklist

## Baseline

- Confirm `docs/specs` exists.
- Confirm canonical files exist:
  - `chronosrefine_functional_requirements.md`
  - `chronosrefine_engineering_requirements.md`
  - `chronosrefine_security_operations_requirements.md`
  - `chronosrefine_nonfunctional_requirements.md`
  - `chronosrefine_design_requirements.md`
  - `ChronosRefine Requirements Coverage Matrix.md`
  - `chronosrefine_implementation_plan.md`
  - `chronosrefine_test_templates.md`

## Drift Checks

- No deprecated assistant-workspace path references.
- No legacy `chronosrefine_prd_final` references.
- Coverage matrix includes phases 1..6.
- Implementation plan includes phases 1..6.
- Implementation plan `Requirements Implemented` counts match matrix phase counts.

## Output

- Report only actionable findings.
- Include absolute file path and line number.
- Recommend minimal patch, not broad refactor.
