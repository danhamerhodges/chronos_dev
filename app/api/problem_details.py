"""RFC 7807 problem-details helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.contracts import ProblemDetail


@dataclass
class ProblemException(Exception):
    title: str
    detail: str
    status_code: int
    type: str = "about:blank"
    errors: list[dict[str, Any]] = field(default_factory=list)


def build_problem(
    request: Request,
    *,
    title: str,
    detail: str,
    status_code: int,
    type: str = "about:blank",
    errors: list[dict[str, Any]] | None = None,
) -> ProblemDetail:
    return ProblemDetail(
        type=type,
        title=title,
        status=status_code,
        detail=detail,
        instance=str(request.url.path),
        errors=errors or [],
        request_id=getattr(request.state, "request_id", None),
    )


def problem_response(problem: ProblemDetail) -> JSONResponse:
    return JSONResponse(status_code=problem.status, content=problem.model_dump(exclude_none=True))


async def problem_exception_handler(request: Request, exc: ProblemException) -> JSONResponse:
    return problem_response(
        build_problem(
            request,
            title=exc.title,
            detail=exc.detail,
            status_code=exc.status_code,
            type=exc.type,
            errors=exc.errors,
        )
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP request failed."
    errors = exc.detail.get("errors", []) if isinstance(exc.detail, dict) else []
    return problem_response(
        build_problem(
            request,
            title="HTTP Error",
            detail=detail,
            status_code=exc.status_code,
            errors=errors,
        )
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for item in exc.errors():
        location = ".".join(str(part) for part in item.get("loc", []) if part != "body")
        errors.append(
            {
                "rule_id": "REQUEST-VALIDATION",
                "severity": "error",
                "field": location or "body",
                "message": item.get("msg", "Invalid request payload."),
            }
        )
    status_code = 400
    if request.method.upper() == "POST" and request.url.path in {"/v1/jobs", "/v1/jobs/estimate"}:
        status_code = 422
    return problem_response(
        build_problem(
            request,
            title="Request Validation Failed",
            detail="Request payload validation failed. Fix the highlighted fields and retry.",
            status_code=status_code,
            errors=errors,
        )
    )
