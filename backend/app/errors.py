from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class BadRequest(AppError):
    status_code = 400
    code = "bad_request"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class InvalidTransition(Conflict):
    code = "invalid_transition"


class TooManyRequests(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str, *, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    content: dict = {"detail": exc.message, "code": exc.code}
    headers = None
    if isinstance(exc, TooManyRequests) and exc.retry_after is not None:
        content["retry_after"] = exc.retry_after
        headers = {"Retry-After": str(exc.retry_after)}
    return JSONResponse(status_code=exc.status_code, content=content, headers=headers)
