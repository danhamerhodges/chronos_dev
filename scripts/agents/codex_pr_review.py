#!/usr/bin/env python3
"""Advisory OpenAI-backed PR review commenter for same-repo GitHub PRs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REVIEW_MARKER = "<!-- codex-pr-review -->"
DEFAULT_MODEL = "gpt-5.4"
MAX_CHANGED_FILES = 60
MAX_PR_BODY_CHARS = 4_000
MAX_DIFF_CHARS = 100_000
MAX_COMMENT_BODY_CHARS = 60_000
MAX_ERROR_TEXT_CHARS = 300
OPENAI_BASE_URL = "https://api.openai.com/v1/responses"
GITHUB_API_BASE = "https://api.github.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an advisory OpenAI-backed PR review and upsert a summary comment.")
    parser.add_argument("--write-summary", default="")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_event() -> dict[str, Any]:
    event_path = os.getenv("GITHUB_EVENT_PATH", "")
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def run_git(args: list[str]) -> str:
    rc, out, err = run_command(["git", *args])
    if rc != 0:
        raise RuntimeError((err or out).strip() or f"git {' '.join(args)} failed")
    return out


def trim_text(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    if limit <= 3:
        return text[:limit], True
    return text[: limit - 3] + "...", True


def extract_output_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text = content.get("text", "")
                if text:
                    parts.append(text)
    return "\n\n".join(parts).strip()


def resolve_project_header_status(project_id: str) -> tuple[str, str]:
    value = project_id.strip()
    if not value:
        return "", "not set"
    if value.startswith("proj_"):
        return value, "enabled"
    return "", "ignored (invalid project id)"


def sanitize_error_text(text: str) -> str:
    collapsed = " ".join(text.split())
    sanitized, _ = trim_text(collapsed, MAX_ERROR_TEXT_CHARS)
    return sanitized or "unknown error"


def extract_api_error_message(service: str, status_code: int, error_body: str) -> str:
    message = ""
    try:
        payload = json.loads(error_body)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message", "")).strip()
        if not message:
            message = str(payload.get("message", "")).strip()
    if not message:
        message = error_body.strip() or f"HTTP {status_code}"
    return f"{service} API error {status_code}: {sanitize_error_text(message)}"


def collect_changed_files(base_sha: str, head_sha: str) -> list[dict[str, Any]]:
    output = run_git(["diff", "--numstat", f"{base_sha}..{head_sha}"])
    changed_files: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        if not raw_line.strip():
            continue
        added, deleted, path = raw_line.split("\t", 2)
        changed_files.append(
            {
                "path": path,
                "added": None if added == "-" else int(added),
                "deleted": None if deleted == "-" else int(deleted),
                "binary": added == "-" or deleted == "-",
            }
        )
    return changed_files


def collect_diff(base_sha: str, head_sha: str) -> tuple[str, bool]:
    diff = run_git(["diff", "--no-color", "--unified=2", f"{base_sha}..{head_sha}"])
    return trim_text(diff, MAX_DIFF_CHARS)


def build_review_input(event: dict[str, Any]) -> dict[str, Any]:
    pr = event.get("pull_request", {})
    base_sha = pr.get("base", {}).get("sha", "")
    head_sha = pr.get("head", {}).get("sha", "")
    if not base_sha or not head_sha:
        raise RuntimeError("Missing base/head SHA in pull request event payload.")

    changed_files = collect_changed_files(base_sha, head_sha)
    diff_excerpt, diff_truncated = collect_diff(base_sha, head_sha)
    pr_body, body_truncated = trim_text(pr.get("body") or "", MAX_PR_BODY_CHARS)

    file_lines = []
    for item in changed_files[:MAX_CHANGED_FILES]:
        stats = "binary" if item["binary"] else f"+{item['added']} -{item['deleted']}"
        file_lines.append(f"- {item['path']} ({stats})")
    if len(changed_files) > MAX_CHANGED_FILES:
        file_lines.append(f"- ... {len(changed_files) - MAX_CHANGED_FILES} more files omitted")

    payload = "\n".join(
        [
            f"Repository: {event.get('repository', {}).get('full_name', 'unknown')}",
            f"PR: #{pr.get('number', 'n/a')} {pr.get('title', '').strip()}",
            f"URL: {pr.get('html_url', '')}",
            f"Base SHA: {base_sha}",
            f"Head SHA: {head_sha}",
            f"Author: {pr.get('user', {}).get('login', 'unknown')}",
            "",
            "PR description:",
            pr_body or "(empty)",
            "",
            "Changed files:",
            "\n".join(file_lines) or "(none)",
            "",
            "Unified diff excerpt:",
            "```diff",
            diff_excerpt or "(empty diff)",
            "```",
        ]
    )
    return {
        "base_sha": base_sha,
        "head_sha": head_sha,
        "changed_files": changed_files,
        "diff_truncated": diff_truncated,
        "pr_body_truncated": body_truncated,
        "review_input": payload,
    }


def build_review_instructions() -> str:
    return (
        "You are a senior software engineer reviewing a GitHub pull request for the ChronosRefine repository. "
        "Review only the provided PR metadata and diff excerpt. "
        "Prioritize correctness bugs, behavioral regressions, security/privacy issues, and missing tests. "
        "Do not praise or restate the diff. Do not suggest broad refactors. "
        "If there are no material findings, say exactly 'No material findings.' "
        "Return concise GitHub-flavored markdown with these sections: "
        "'## Findings', '## Residual Risks', and '## Recommendation'. "
        "Each finding must mention the affected file path and why it matters."
    )


def call_openai_review(*, review_input: str, model: str, project_id: str) -> tuple[str, dict[str, Any]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    body = {
        "model": model,
        "instructions": build_review_instructions(),
        "input": review_input,
        "max_output_tokens": 1400,
        "store": False,
        "text": {"format": {"type": "text"}},
        "metadata": {"source": "github-actions", "automation": "codex-pr-review"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if project_id:
        headers["OpenAI-Project"] = project_id

    request = urllib.request.Request(
        OPENAI_BASE_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(extract_api_error_message("OpenAI", exc.code, error_body)) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {sanitize_error_text(str(exc.reason))}") from exc

    text = extract_output_text(payload)
    if not text:
        raise RuntimeError("OpenAI API returned no output_text content.")
    return text, payload


def github_request(method: str, path: str, token: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{GITHUB_API_BASE}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(extract_api_error_message("GitHub", exc.code, error_body)) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API request failed: {sanitize_error_text(str(exc.reason))}") from exc


def list_issue_comments(*, owner: str, repo: str, issue_number: int, token: str) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = github_request(
            "GET",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments?per_page=100&page={page}",
            token,
        )
        if not isinstance(batch, list):
            raise RuntimeError("GitHub API returned a non-list issue comments payload.")
        comments.extend(batch)
        if len(batch) < 100:
            return comments
        page += 1


def upsert_pr_comment(*, repo_full_name: str, issue_number: int, token: str, body: str) -> dict[str, Any]:
    owner, repo = repo_full_name.split("/", 1)
    comments = list_issue_comments(owner=owner, repo=repo, issue_number=issue_number, token=token)
    existing = next((item for item in comments if REVIEW_MARKER in item.get("body", "")), None)
    if existing:
        return github_request("PATCH", f"/repos/{owner}/{repo}/issues/comments/{existing['id']}", token, {"body": body})
    return github_request("POST", f"/repos/{owner}/{repo}/issues/{issue_number}/comments", token, {"body": body})


def render_comment_body(
    *,
    review_text: str,
    model: str,
    project_header_status: str,
    changed_files_count: int,
    base_sha: str,
    head_sha: str,
    diff_truncated: bool,
    pr_body_truncated: bool,
) -> str:
    truncation_bits = []
    if pr_body_truncated:
        truncation_bits.append("PR body truncated")
    if diff_truncated:
        truncation_bits.append("diff truncated")
    truncation_line = ", ".join(truncation_bits) if truncation_bits else "none"
    header = "\n".join(
        [
            REVIEW_MARKER,
            "## Codex PR Review",
            "",
            f"- Model: `{model}`",
            f"- OpenAI project header: `{project_header_status}`",
            f"- Reviewed files: `{changed_files_count}`",
            f"- Base..Head: `{base_sha[:12]}..{head_sha[:12]}`",
            f"- Input truncation: `{truncation_line}`",
            "",
        ]
    )
    review_section = review_text.strip()
    body = f"{header}\n{review_section}".strip() + "\n"
    if len(body) <= MAX_COMMENT_BODY_CHARS:
        return body

    truncation_note = "\n\n_Review text truncated to fit GitHub comment limits._"
    available = max(MAX_COMMENT_BODY_CHARS - len(header) - len(truncation_note) - 2, 0)
    truncated_review, _ = trim_text(review_section, available)
    return f"{header}\n{truncated_review}{truncation_note}".strip() + "\n"


def render_status_summary(title: str, details: list[str]) -> str:
    lines = [f"## {title}", ""]
    lines.extend(f"- {detail}" for detail in details)
    return "\n".join(lines) + "\n"


def append_step_summary(path_str: str, summary: str) -> None:
    path = Path(path_str)
    prefix = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing and not existing.endswith("\n"):
            prefix = "\n"
    with path.open("a", encoding="utf-8") as handle:
        if prefix:
            handle.write(prefix)
        handle.write(summary)


def main() -> int:
    args = parse_args()
    event = load_event()
    summary = ""
    exit_code = 0
    result: dict[str, Any] = {"status": "skipped"}

    try:
        pr = event.get("pull_request", {})
        repo_full_name = event.get("repository", {}).get("full_name", "")
        issue_number = int(pr.get("number", 0) or 0)
        github_token = os.getenv("GITHUB_TOKEN", "").strip()
        project_id, project_header_status = resolve_project_header_status(os.getenv("OPENAI_PROJECT_ID", ""))
        model = os.getenv("OPENAI_REVIEW_MODEL", "").strip() or DEFAULT_MODEL

        if not pr or not repo_full_name or not issue_number:
            summary = render_status_summary("Codex PR Review", ["Skipped: no pull request event payload found."])
        elif not github_token:
            summary = render_status_summary("Codex PR Review", ["Skipped: GITHUB_TOKEN is not configured."])
        elif not os.getenv("OPENAI_API_KEY", "").strip():
            summary = render_status_summary("Codex PR Review", ["Skipped: OPENAI_API_KEY is not configured."])
        else:
            review_bundle = build_review_input(event)
            review_text, api_payload = call_openai_review(
                review_input=review_bundle["review_input"],
                model=model,
                project_id=project_id,
            )
            comment_body = render_comment_body(
                review_text=review_text,
                model=model,
                project_header_status=project_header_status,
                changed_files_count=len(review_bundle["changed_files"]),
                base_sha=review_bundle["base_sha"],
                head_sha=review_bundle["head_sha"],
                diff_truncated=review_bundle["diff_truncated"],
                pr_body_truncated=review_bundle["pr_body_truncated"],
            )
            comment = upsert_pr_comment(
                repo_full_name=repo_full_name,
                issue_number=issue_number,
                token=github_token,
                body=comment_body,
            )
            summary = render_status_summary(
                "Codex PR Review",
                [
                    f"Status: `commented`",
                    f"PR: `#{issue_number}`",
                    f"Model: `{model}`",
                    f"OpenAI project header: `{project_header_status}`",
                    f"Reviewed files: `{len(review_bundle['changed_files'])}`",
                    f"Diff truncated: `{'yes' if review_bundle['diff_truncated'] else 'no'}`",
                    f"Comment URL: {comment.get('html_url', 'n/a')}",
                    f"OpenAI response ID: `{api_payload.get('id', 'unknown')}`",
                ],
            )
            result = {
                "status": "commented",
                "model": model,
                "project_header": project_header_status,
                "reviewed_files": len(review_bundle["changed_files"]),
                "diff_truncated": review_bundle["diff_truncated"],
                "comment_url": comment.get("html_url", ""),
                "response_id": api_payload.get("id", ""),
            }
    except Exception as exc:  # pragma: no cover - error path exercised via workflow runtime
        reason = sanitize_error_text(str(exc))
        summary = render_status_summary("Codex PR Review", [f"Status: `error`", f"Reason: `{reason}`"])
        result = {"status": "error", "error": reason}
        exit_code = 1

    if args.write_summary:
        append_step_summary(args.write_summary, summary)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(summary)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
