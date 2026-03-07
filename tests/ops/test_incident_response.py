"""Maps to: OPS-003, NFR-002"""

from app.services.runtime_ops import emit_incident, evaluate_job_slo, incident_history


def test_incident_records_capture_postmortem_due_date_for_p1() -> None:
    incident = emit_incident(
        severity="P1",
        source_signal="processing-time-slo",
        summary="Processing time SLO breached.",
        metadata={"job_id": "job-incident-1"},
    )

    assert incident["severity"] == "P1"
    assert incident["postmortem_due_at"] is not None
    assert incident_history()[0]["incident_key"] == incident["incident_key"]


def test_slo_breach_emits_incident_record() -> None:
    summary = evaluate_job_slo(
        {
            "job_id": "job-slo-breach",
            "plan_tier": "museum",
            "estimated_duration_seconds": 10,
            "stage_timings": {"total_ms": 25000},
        }
    )

    assert summary["compliant"] is False
    assert any(item["source_signal"] == "processing-time-slo" for item in incident_history())
