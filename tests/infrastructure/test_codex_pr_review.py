"""Maps to: OPS-001"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


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
        diff_paths_sent=2,
        base_sha="abcdef1234567890",
        head_sha="fedcba0987654321",
        diff_truncated=True,
        pr_body_truncated=False,
    )

    assert module.REVIEW_MARKER in rendered
    assert "## Codex PR Review" in rendered
    assert "OpenAI project header: `enabled`" in rendered
    assert "Changed files in PR: `3`" in rendered
    assert "Diff paths sent to OpenAI: `2`" in rendered
    assert "Input truncation: `diff truncated`" in rendered
    assert "## Findings" in rendered


def test_render_comment_body_truncates_oversized_review_text() -> None:
    module = _load_module()

    rendered = module.render_comment_body(
        review_text="A" * (module.MAX_COMMENT_BODY_BYTES + 500),
        model="gpt-5.4",
        project_header_status="enabled",
        changed_files_count=3,
        diff_paths_sent=2,
        base_sha="abcdef1234567890",
        head_sha="fedcba0987654321",
        diff_truncated=False,
        pr_body_truncated=False,
    )

    assert len(rendered.encode("utf-8")) <= module.MAX_COMMENT_BODY_BYTES
    assert "_Review text truncated to fit GitHub comment limits._" in rendered
    assert module.REVIEW_MARKER in rendered


def test_render_comment_body_truncates_by_utf8_bytes() -> None:
    module = _load_module()

    rendered = module.render_comment_body(
        review_text="é" * module.MAX_COMMENT_BODY_BYTES,
        model="gpt-5.4",
        project_header_status="enabled",
        changed_files_count=3,
        diff_paths_sent=2,
        base_sha="abcdef1234567890",
        head_sha="fedcba0987654321",
        diff_truncated=False,
        pr_body_truncated=False,
    )

    assert len(rendered.encode("utf-8")) <= module.MAX_COMMENT_BODY_BYTES
    assert "_Review text truncated to fit GitHub comment limits._" in rendered


def test_resolve_project_header_status_ignores_non_project_values() -> None:
    module = _load_module()

    project_id, status = module.resolve_project_header_status("chronos-dev")

    assert project_id == ""
    assert status == "ignored (invalid project id)"


def test_extract_api_error_message_prefers_sanitized_api_message() -> None:
    module = _load_module()

    message = module.extract_api_error_message(
        "OpenAI",
        401,
        '{"error":{"message":"OpenAI-Project header should match project for API key","type":"invalid_request_error","debug":"hidden"}}',
    )

    assert message == "OpenAI API error 401: OpenAI-Project header should match project for API key"
    assert "hidden" not in message
    assert "invalid_request_error" not in message


def test_redact_sensitive_diff_content_redacts_secret_like_lines() -> None:
    module = _load_module()
    diff = "\n".join(
        [
            "diff --git a/.env b/.env",
            "--- a/.env",
            "+++ b/.env",
            '+OPENAI_API_KEY="sk-test-secret-value"',
            '+NORMAL_VALUE="safe"',
        ]
    )

    redacted = module.redact_sensitive_diff_content(diff)

    assert '+[REDACTED SENSITIVE CONTENT]' in redacted
    assert '+NORMAL_VALUE="safe"' in redacted
    assert 'sk-test-secret-value' not in redacted


def test_redact_sensitive_diff_content_redacts_common_secret_patterns() -> None:
    module = _load_module()
    diff = "\n".join(
        [
            "diff --git a/app/config.py b/app/config.py",
            "--- a/app/config.py",
            "+++ b/app/config.py",
            '+AUTHORIZATION = "Bearer super-secret-token"',
            '+DB_PASSWORD = "super-secret-password"',
            "+PRIVATE_KEY = '-----BEGIN PRIVATE KEY-----'",
        ]
    )

    redacted = module.redact_sensitive_diff_content(diff)

    assert redacted.count("[REDACTED SENSITIVE CONTENT]") == 3
    assert "super-secret-token" not in redacted
    assert "super-secret-password" not in redacted
    assert "BEGIN PRIVATE KEY" not in redacted


def test_select_reviewable_diff_paths_omits_sensitive_and_excess_paths() -> None:
    module = _load_module()
    changed_files = [
        {"path": ".env", "added": 1, "deleted": 0, "binary": False},
        {"path": "app/main.py", "added": 5, "deleted": 2, "binary": False},
        {"path": "secrets/service.key", "added": 1, "deleted": 0, "binary": False},
    ] + [
        {"path": f"tests/test_{idx}.py", "added": 1, "deleted": 0, "binary": False}
        for idx in range(module.MAX_DIFF_FILES + 2)
    ]

    diff_paths, filtered_count, omitted_count = module.select_reviewable_diff_paths(changed_files)

    assert ".env" not in diff_paths
    assert "secrets/service.key" not in diff_paths
    assert "app/main.py" in diff_paths
    assert len(diff_paths) == module.MAX_DIFF_FILES
    assert filtered_count == 2
    assert omitted_count == 3


def test_is_sensitive_path_matches_top_level_secret_directories() -> None:
    module = _load_module()

    assert module.is_sensitive_path("secrets/service-account.json") is True
    assert module.is_sensitive_path("tokens/cache.txt") is True


def test_collect_changed_files_handles_rename_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setattr(
        module,
        "run_git_bytes",
        lambda args: b"1\t0\t\0src/old.py\0src/new.py\0",
    )

    changed_files = module.collect_changed_files("abc123", "def456")

    assert changed_files == [
        {
            "path": "src/new.py",
            "display_path": "src/old.py => src/new.py",
            "added": 1,
            "deleted": 0,
            "binary": False,
        }
    ]


def test_collect_changed_files_handles_real_git_rename_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    def run_git(*args: str) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip()

    run_git("init", "-q")
    run_git("config", "user.email", "test@example.com")
    run_git("config", "user.name", "Chronos Test")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/old.py").write_text("print('old')\n", encoding="utf-8")
    run_git("add", "src/old.py")
    run_git("commit", "-qm", "base")
    base_sha = run_git("rev-parse", "HEAD")
    run_git("mv", "src/old.py", "src/new.py")
    with (tmp_path / "src/new.py").open("a", encoding="utf-8") as handle:
        handle.write("print('new')\n")
    run_git("commit", "-am", "rename")
    head_sha = run_git("rev-parse", "HEAD")

    changed_files = module.collect_changed_files(base_sha, head_sha)

    assert changed_files == [
        {
            "path": "src/new.py",
            "display_path": "src/old.py => src/new.py",
            "added": 1,
            "deleted": 0,
            "binary": False,
        }
    ]


def test_ensure_commit_available_fetches_missing_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    exists_checks = iter([False, True])
    seen_git_args: list[list[str]] = []

    monkeypatch.setattr(module, "git_commit_exists", lambda sha: next(exists_checks))
    monkeypatch.setattr(module, "run_git", lambda args: seen_git_args.append(args) or "")

    module.ensure_commit_available("abc123", "main")

    assert seen_git_args == [["fetch", "--no-tags", "--depth=1", "origin", "abc123"]]


def test_ensure_commit_available_falls_back_to_ref_when_sha_fetch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    exists_checks = iter([False, True])
    seen_git_args: list[list[str]] = []

    def fake_run_git(args: list[str]) -> str:
        seen_git_args.append(args)
        if args[-1] == "abc123":
            raise RuntimeError("sha fetch failed")
        return ""

    monkeypatch.setattr(module, "git_commit_exists", lambda sha: next(exists_checks))
    monkeypatch.setattr(module, "run_git", fake_run_git)

    module.ensure_commit_available("abc123", "main")

    assert seen_git_args == [
        ["fetch", "--no-tags", "--depth=1", "origin", "abc123"],
        ["fetch", "--no-tags", "--depth=1", "origin", "main"],
    ]


def test_ensure_commit_available_raises_when_commit_stays_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "git_commit_exists", lambda sha: False)
    monkeypatch.setattr(module, "run_git", lambda args: "")

    with pytest.raises(RuntimeError, match=r"Failed to fetch commit abc123 from origin targets \[abc123, main\]\."):
        module.ensure_commit_available("abc123", "main")


def test_build_review_input_includes_changed_files_and_diff_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    event = {
        "repository": {"full_name": "danhamerhodges/chronos_dev"},
        "pull_request": {
            "number": 3,
            "title": "ci: add OpenAI-backed PR review workflow",
            "html_url": "https://github.com/danhamerhodges/chronos_dev/pull/3",
            "body": "Adds a reviewer.",
            "user": {"login": "danhamerhodges"},
            "base": {"sha": "abc123", "ref": "main"},
            "head": {"sha": "def456", "ref": "codex/pr-review-automation"},
        },
    }
    ensured_commits: list[tuple[str, str]] = []

    monkeypatch.setattr(
        module,
        "collect_changed_files",
        lambda base_sha, head_sha: [
            {"path": "scripts/agents/codex_pr_review.py", "added": 12, "deleted": 3, "binary": False},
            {"path": ".env", "added": 1, "deleted": 0, "binary": False},
        ],
    )
    monkeypatch.setattr(module, "collect_diff", lambda base_sha, head_sha, paths: ("diff --git a/x b/x", True))
    monkeypatch.setattr(module, "ensure_commit_available", lambda sha, ref: ensured_commits.append((sha, ref)))

    bundle = module.build_review_input(event)

    assert bundle["base_sha"] == "abc123"
    assert bundle["head_sha"] == "def456"
    assert bundle["diff_truncated"] is True
    assert bundle["pr_body_truncated"] is False
    assert bundle["diff_paths_sent"] == 1
    assert "- scripts/agents/codex_pr_review.py (+12 -3)" in bundle["review_input"]
    assert "Diff paths sent to OpenAI: 1" in bundle["review_input"]
    assert "Diff paths filtered from OpenAI payload: 1" in bundle["review_input"]
    assert "Diff paths omitted from OpenAI payload: 0" in bundle["review_input"]
    assert "diff --git a/x b/x" in bundle["review_input"]
    assert ensured_commits == [("abc123", "main"), ("def456", "codex/pr-review-automation")]


def test_upsert_pr_comment_paginates_before_patching(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    seen_paths: list[tuple[str, str, object | None]] = []

    def fake_github_request(method: str, path: str, token: str, body=None):
        seen_paths.append((method, path, body))
        if method == "GET" and path.endswith("page=1"):
            return [{"id": idx, "body": "other comment"} for idx in range(100)]
        if method == "GET" and path.endswith("page=2"):
            return [
                {
                    "id": 777,
                    "body": f"{module.REVIEW_MARKER}\nold body",
                    "user": {"login": "codex-review[bot]", "type": "Bot"},
                    "performed_via_github_app": {"slug": "github-actions"},
                }
            ]
        if method == "PATCH":
            return {"id": 777, "html_url": "https://example.com/comment/777", "body": body["body"]}
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(module, "github_request", fake_github_request)

    result = module.upsert_pr_comment(
        repo_full_name="danhamerhodges/chronos_dev",
        issue_number=3,
        token="ghs_test",
        body="updated body",
    )

    assert result["html_url"] == "https://example.com/comment/777"
    assert [item[1] for item in seen_paths[:2]] == [
        "/repos/danhamerhodges/chronos_dev/issues/3/comments?per_page=100&page=1",
        "/repos/danhamerhodges/chronos_dev/issues/3/comments?per_page=100&page=2",
    ]
    assert seen_paths[2][0] == "PATCH"
    assert seen_paths[2][1] == "/repos/danhamerhodges/chronos_dev/issues/comments/777"


def test_upsert_pr_comment_uses_legacy_bot_login_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()

    def fake_github_request(method: str, path: str, token: str, body=None):
        if method == "GET":
            return [
                {
                    "id": 303,
                    "body": f"{module.REVIEW_MARKER}\nold body",
                    "user": {"login": "github-actions[bot]", "type": "Bot"},
                }
            ]
        if method == "PATCH":
            return {"id": 303, "html_url": "https://example.com/comment/303", "body": body["body"]}
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(module, "github_request", fake_github_request)

    result = module.upsert_pr_comment(
        repo_full_name="danhamerhodges/chronos_dev",
        issue_number=3,
        token="ghs_test",
        body="updated body",
    )

    assert result["html_url"] == "https://example.com/comment/303"


def test_upsert_pr_comment_updates_newest_owned_marker_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    seen_paths: list[tuple[str, str, object | None]] = []

    def fake_github_request(method: str, path: str, token: str, body=None):
        seen_paths.append((method, path, body))
        if method == "GET":
            return [
                {
                    "id": 101,
                    "body": f"{module.REVIEW_MARKER}\nolder body",
                    "user": {"login": "github-actions[bot]", "type": "Bot"},
                    "performed_via_github_app": {"slug": "github-actions"},
                },
                {
                    "id": 202,
                    "body": f"{module.REVIEW_MARKER}\nnewer body",
                    "user": {"login": "github-actions[bot]", "type": "Bot"},
                    "performed_via_github_app": {"slug": "github-actions"},
                },
            ]
        if method == "PATCH":
            return {"id": 202, "html_url": "https://example.com/comment/202", "body": body["body"]}
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(module, "github_request", fake_github_request)

    result = module.upsert_pr_comment(
        repo_full_name="danhamerhodges/chronos_dev",
        issue_number=3,
        token="ghs_test",
        body="updated body",
    )

    assert result["html_url"] == "https://example.com/comment/202"
    assert seen_paths[-1][1] == "/repos/danhamerhodges/chronos_dev/issues/comments/202"


def test_upsert_pr_comment_does_not_overwrite_non_bot_marker_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    seen_paths: list[tuple[str, str, object | None]] = []

    def fake_github_request(method: str, path: str, token: str, body=None):
        seen_paths.append((method, path, body))
        if method == "GET" and path.endswith("page=1"):
            return [{"id": 101, "body": f"{module.REVIEW_MARKER}\nhuman note", "user": {"login": "alice"}}]
        if method == "POST":
            return {"id": 202, "html_url": "https://example.com/comment/202", "body": body["body"]}
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(module, "github_request", fake_github_request)

    result = module.upsert_pr_comment(
        repo_full_name="danhamerhodges/chronos_dev",
        issue_number=3,
        token="ghs_test",
        body="new body",
    )

    assert result["html_url"] == "https://example.com/comment/202"
    assert seen_paths[-1][0] == "POST"
    assert "/repos/danhamerhodges/chronos_dev/issues/3/comments" == seen_paths[-1][1]


def test_upsert_pr_comment_does_not_overwrite_other_bot_marker_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    seen_paths: list[tuple[str, str, object | None]] = []

    def fake_github_request(method: str, path: str, token: str, body=None):
        seen_paths.append((method, path, body))
        if method == "GET":
            return [
                {
                    "id": 404,
                    "body": f"{module.REVIEW_MARKER}\nforeign automation",
                    "user": {"login": "other-bot[bot]", "type": "Bot"},
                    "performed_via_github_app": {"slug": "other-app"},
                }
            ]
        if method == "POST":
            return {"id": 505, "html_url": "https://example.com/comment/505", "body": body["body"]}
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(module, "github_request", fake_github_request)

    result = module.upsert_pr_comment(
        repo_full_name="danhamerhodges/chronos_dev",
        issue_number=3,
        token="ghs_test",
        body="new body",
    )

    assert result["html_url"] == "https://example.com/comment/505"
    assert seen_paths[-1][0] == "POST"


def test_main_returns_zero_for_intentional_skip(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    module = _load_module()

    monkeypatch.setattr(module, "parse_args", lambda: SimpleNamespace(write_summary="", json=False))
    monkeypatch.setattr(module, "load_event", lambda: {})
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_PROJECT_ID", raising=False)

    exit_code = module.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Skipped: no pull request event payload found." in captured.out


def test_main_returns_zero_and_prints_summary_on_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    module = _load_module()
    event = {
        "repository": {"full_name": "danhamerhodges/chronos_dev"},
        "pull_request": {"number": 3},
    }
    summary_path = tmp_path / "step-summary.md"
    summary_path.write_text("## Existing Summary\n", encoding="utf-8")

    monkeypatch.setattr(module, "parse_args", lambda: SimpleNamespace(write_summary=str(summary_path), json=False))
    monkeypatch.setattr(module, "load_event", lambda: event)
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "proj_123")
    monkeypatch.setattr(
        module,
        "build_review_input",
        lambda event_payload: {
            "base_sha": "abc123",
            "head_sha": "def456",
            "changed_files": [{"path": "scripts/agents/codex_pr_review.py"}],
            "diff_paths_sent": 1,
            "diff_truncated": False,
            "pr_body_truncated": False,
            "review_input": "review me",
        },
    )
    monkeypatch.setattr(
        module,
        "call_openai_review",
        lambda **kwargs: ("## Findings\nNo material findings.\n\n## Residual Risks\n- none\n\n## Recommendation\nApprove.", {"id": "resp_123"}),
    )
    monkeypatch.setattr(module, "upsert_pr_comment", lambda **kwargs: {"html_url": "https://example.com/comment/123"})

    exit_code = module.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Status: `commented`" in captured.out
    assert "OpenAI project header: `enabled`" in captured.out
    assert "Comment URL: https://example.com/comment/123" in captured.out
    summary = summary_path.read_text(encoding="utf-8")
    assert summary.startswith("## Existing Summary\n")
    assert "## Codex PR Review" in summary


def test_main_returns_non_zero_for_review_execution_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_module()
    event = {
        "repository": {"full_name": "danhamerhodges/chronos_dev"},
        "pull_request": {"number": 3},
    }

    monkeypatch.setattr(module, "parse_args", lambda: SimpleNamespace(write_summary="", json=False))
    monkeypatch.setattr(module, "load_event", lambda: event)
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "proj_123")

    def _raise_review_error(_: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "build_review_input", _raise_review_error)

    exit_code = module.main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Status: `error`" in captured.out
    assert "boom" in captured.out


def test_append_step_summary_preserves_existing_content(tmp_path: Path) -> None:
    module = _load_module()
    summary_path = tmp_path / "summary.md"
    summary_path.write_text("existing summary", encoding="utf-8")

    module.append_step_summary(str(summary_path), "## Codex PR Review\n- Status: `commented`\n")

    assert summary_path.read_text(encoding="utf-8") == (
        "existing summary\n## Codex PR Review\n- Status: `commented`\n"
    )


def test_trim_text_reports_truncation() -> None:
    module = _load_module()

    text, truncated = module.trim_text("abcdefghij", 6)

    assert truncated is True
    assert text == "abc..."
