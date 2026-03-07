"""Maps to: OPS-001"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[2]
    script_path = root / "scripts/agents/codex_pr_review.py"
    spec = importlib.util.spec_from_file_location("codex_pr_review", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_extract_output_text_reads_message_content() -> None:
    module = _load_module()
    payload = {
        "output": [
            {"type": "tool_call", "content": []},
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "First finding."},
                    {"type": "output_text", "text": "Second finding."},
                ],
            },
        ]
    }

    assert module.extract_output_text(payload) == "First finding.\n\nSecond finding."


def test_render_comment_body_includes_marker_and_metadata() -> None:
    module = _load_module()

    rendered = module.render_comment_body(
        review_text="## Findings\n- No material findings.",
        model="gpt-5.4",
        project_header_status="enabled",
        changed_files_count=3,
        base_sha="abcdef1234567890",
        head_sha="fedcba0987654321",
        diff_truncated=True,
        pr_body_truncated=False,
    )

    assert module.REVIEW_MARKER in rendered
    assert "## Codex PR Review" in rendered
    assert "OpenAI project header: `enabled`" in rendered
    assert "Input truncation: `diff truncated`" in rendered
    assert "## Findings" in rendered


def test_resolve_project_header_status_ignores_non_project_values() -> None:
    module = _load_module()

    project_id, status = module.resolve_project_header_status("chronos-dev")

    assert project_id == ""
    assert status == "ignored (invalid project id)"


def test_trim_text_reports_truncation() -> None:
    module = _load_module()

    text, truncated = module.trim_text("abcdefghij", 6)

    assert truncated is True
    assert text == "abc..."
