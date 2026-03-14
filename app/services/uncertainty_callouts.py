"""Packet 4C uncertainty-callout derivation."""

from __future__ import annotations

from typing import Any

from app.api.problem_details import ProblemException
from app.db.phase2_store import JobRepository

_SEGMENT_CALLOUT_MAP: dict[str, dict[str, str]] = {
    "texture_energy_margin_low": {
        "code": "texture_loss_risk",
        "title": "Texture loss risk",
        "message": "Texture-energy metrics are close to the acceptance threshold for this segment.",
        "metric_key": "e_hf",
    },
    "spectral_slope_margin_low": {
        "code": "spectral_boundary_risk",
        "title": "Spectral boundary risk",
        "message": "Spectral balance is close to the acceptance threshold for this segment.",
        "metric_key": "s_ls_db",
    },
    "temporal_coherence_margin_low": {
        "code": "temporal_coherence_risk",
        "title": "Temporal coherence risk",
        "message": "Temporal coherence is close to the acceptance threshold for this segment.",
        "metric_key": "t_tc",
    },
}


def _non_negative_seconds(raw_value: Any) -> float:
    try:
        return max(float(raw_value), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _normalized_confidence(raw_value: Any) -> float | None:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    if 0.0 <= value <= 1.0:
        return value
    return None


class UncertaintyCalloutService:
    def __init__(self) -> None:
        self._repo = JobRepository()

    def list_callouts(
        self,
        job_id: str,
        *,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> dict[str, object]:
        job = self._repo.get_job(job_id, owner_user_id=owner_user_id, access_token=access_token)
        if job is None:
            raise ProblemException(
                title="Not Found",
                detail="Job not found for the current user.",
                status_code=404,
            )

        return {
            "job_id": job_id,
            "status": job["status"],
            "callouts": self.build_callouts(job, self._repo.list_segments(job_id, owner_user_id=owner_user_id, access_token=access_token)),
        }

    def build_callouts(
        self,
        job: dict[str, Any],
        segments: list[dict[str, Any]],
    ) -> list[dict[str, object]]:
        callouts: list[dict[str, object]] = []

        global_callout = self._global_detection_callout(job)
        if global_callout is not None:
            callouts.append(global_callout)

        for segment in sorted(segments, key=lambda item: int(item.get("segment_index", 0) or 0)):
            callouts.extend(self._segment_callouts(job_id=str(job["job_id"]), segment=segment))
        return callouts

    def _global_detection_callout(self, job: dict[str, Any]) -> dict[str, object] | None:
        era_profile = job.get("era_profile") or {}
        confidence = era_profile.get("gemini_confidence")
        manual_confirmation_required = bool(era_profile.get("manual_confirmation_required"))

        if confidence is None and not manual_confirmation_required:
            return None

        confidence_value = _normalized_confidence(confidence)
        low_confidence = confidence is not None and (confidence_value is None or confidence_value < 0.70)
        if not manual_confirmation_required and not low_confidence:
            return None

        duration_seconds = _non_negative_seconds(job.get("estimated_duration_seconds"))
        detection_snapshot = (job.get("config") or {}).get("detection_snapshot") or {}
        detected_era = str(detection_snapshot.get("era") or job.get("era_profile", {}).get("capture_medium") or "the current media")
        if manual_confirmation_required:
            detail = "Era detection required manual confirmation. Review the restored output carefully."
        elif confidence_value is None:
            detail = f"Era detection confidence for {detected_era} could not be validated. Review the restored output carefully."
        else:
            detail = f"Era detection confidence for {detected_era} remained below 0.70. Review the restored output carefully."

        return {
            "callout_id": f"{job['job_id']}:global:low-confidence-era",
            "code": "low_confidence_era_classification",
            "severity": "warning",
            "title": "Low-confidence era classification",
            "message": detail,
            "scope": "global",
            "time_range_seconds": {
                "start": 0.0,
                "end": duration_seconds,
            },
            "source": {
                "metric_key": "gemini_confidence",
            },
        }

    def _segment_callouts(self, *, job_id: str, segment: dict[str, Any]) -> list[dict[str, object]]:
        segment_index = int(segment.get("segment_index", 0) or 0)
        start_seconds = _non_negative_seconds(segment.get("segment_start_seconds"))
        end_seconds = _non_negative_seconds(segment.get("segment_end_seconds"))
        callouts: list[dict[str, object]] = []
        seen_callout_ids: set[str] = set()

        for slug in segment.get("uncertainty_callouts") or []:
            mapped = _SEGMENT_CALLOUT_MAP.get(str(slug))
            if mapped is None:
                continue
            callout_id = f"{job_id}:segment:{segment_index}:{mapped['code']}"
            if callout_id in seen_callout_ids:
                continue
            seen_callout_ids.add(callout_id)
            callouts.append(
                {
                    "callout_id": callout_id,
                    "code": mapped["code"],
                    "severity": "warning",
                    "title": mapped["title"],
                    "message": mapped["message"],
                    "scope": "segment",
                    "time_range_seconds": {
                        "start": start_seconds,
                        "end": end_seconds,
                    },
                    "source": {
                        "segment_index": segment_index,
                        "metric_key": mapped["metric_key"],
                    },
                }
            )

        return callouts
