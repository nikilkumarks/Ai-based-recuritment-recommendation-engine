"""RFC 7807 problem+json errors. Do not put secrets or resume text in details."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    title = "Internal Server Error"
    type_uri = "about:blank"

    def __init__(
        self,
        detail: str,
        *,
        code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        if code is not None:
            self.code = code
        self.metadata = metadata or {}


class UnauthenticatedError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"
    title = "Unauthenticated"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    title = "Forbidden"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"
    title = "Conflict"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    title = "Not Found"


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    title = "Too Many Requests"


class UnprocessableError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    title = "Unprocessable Entity"


class InvalidDocumentError(AppError):
    status_code = 400
    code = "INVALID_DOCUMENT"
    title = "Invalid Document"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"
    title = "Payload Too Large"


class UnsupportedMediaError(AppError):
    status_code = 415
    code = "UNSUPPORTED_MEDIA_TYPE"
    title = "Unsupported Media Type"


class IncompatibleEmbeddingError(AppError):
    status_code = 422
    code = "EMBEDDING_INCOMPATIBLE"
    title = "Incompatible Embedding"


def problem_body(
    *,
    status: int,
    title: str,
    detail: str,
    code: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
    }
    if extras:
        body.update(extras)
    return body


def _json_problem(body: dict[str, Any], status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=body, media_type="application/problem+json")


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    extras = dict(exc.metadata) if exc.metadata else None
    return _json_problem(
        problem_body(
            status=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            code=exc.code,
            extras=extras,
        ),
        exc.status_code,
    )


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    title = "Error"
    code = "HTTP_ERROR"
    if exc.status_code == 401:
        title, code = "Unauthenticated", "UNAUTHENTICATED"
    elif exc.status_code == 403:
        title, code = "Forbidden", "FORBIDDEN"
    elif exc.status_code == 404:
        title, code = "Not Found", "NOT_FOUND"
    elif exc.status_code == 405:
        title, code = "Method Not Allowed", "METHOD_NOT_ALLOWED"
    return _json_problem(
        problem_body(status=exc.status_code, title=title, detail=detail, code=code),
        exc.status_code,
    )


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()) if part != "body")
        errors.append({"field": loc or "body", "message": err.get("msg", "Invalid value.")})
    return _json_problem(
        problem_body(
            status=422,
            title="Unprocessable Entity",
            detail="Request validation failed.",
            code="VALIDATION_ERROR",
            extras={"errors": errors},
        ),
        422,
    )
