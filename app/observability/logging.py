"""Structured logging helpers for OPS-001."""

from __future__ import annotations

import json
import logging
import re
import sys

from app.config import settings


_STANDARD_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+"), r"\1[REDACTED]"),
    (re.compile(r"(apikey=)[^&\s]+"), r"\1[REDACTED]"),
    (re.compile(r"('apikey',\s*b')[^']+"), r"\1[REDACTED]"),
    (re.compile(r"('authorization',\s*b'Bearer\s+)[^']+"), r"\1[REDACTED]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP]"),
    (re.compile(r"/Users/[^/\s]+"), "/Users/[REDACTED_USER]"),
)
_STRICT_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bjob_[A-Za-z0-9\-]+\b"), "[REDACTED_JOB]"),
    (re.compile(r"gs://[^\s]+"), "gs://[REDACTED_BUCKET]/[REDACTED_OBJECT]"),
    (re.compile(r"\b(\d{4}-\d{2}-\d{2})T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\b"), r"\1"),
    (re.compile(r"\b/[A-Za-z0-9._/\-]+\b"), "[REDACTED_PATH]"),
)


def _redact_message(message: str, mode: str = "standard") -> str:
    if mode == "none":
        return message
    redacted = message
    for pattern, replacement in _STANDARD_REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    if mode == "strict":
        for pattern, replacement in _STRICT_REDACTION_PATTERNS:
            redacted = pattern.sub(replacement, redacted)
    return redacted


class JsonFormatter(logging.Formatter):
    def __init__(self, *, redaction_mode: str | None = None) -> None:
        super().__init__()
        self.redaction_mode = redaction_mode or settings.log_redaction_mode or "standard"

    def format(self, record: logging.LogRecord) -> str:
        message = _redact_message(record.getMessage(), mode=self.redaction_mode)
        payload = {
            "level": record.levelname,
            "message": message,
            "logger": record.name,
            "trace_id": getattr(record, "trace_id", None),
            "span_id": getattr(record, "span_id", None),
            "request_id": getattr(record, "request_id", None),
        }
        return json.dumps(payload)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]

    for logger_name in ("httpx", "httpcore", "hpack", "urllib3", "stripe"):
        logging.getLogger(logger_name).setLevel(logging.INFO)
