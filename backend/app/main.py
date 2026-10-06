import logging
import re

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.errors import AppError, app_error_handler
from app.routers import (
    agents,
    auth,
    files,
    house_search,
    inspections,
    nearby,
    properties,
    reference,
    reports,
    reservations,
    reviewer,
    verification,
)
from app.services import storage

_SECRET_RE = re.compile(r"(?i)(password|token|secret|authorization)([\"']?\s*[:=]\s*[\"']?)([^\s\"',}]+)")


class RedactSecretsFilter(logging.Filter):
    """Belt and braces: never let credentials reach the logs even if someone logs a payload."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _SECRET_RE.sub(r"\1\2[redacted]", record.msg)
        return True


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    for handler in logging.getLogger().handlers:
        handler.addFilter(RedactSecretsFilter())


async def _validation_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        {
            "field": ".".join(str(p) for p in e.get("loc", [])[1:]),
            "message": str(e.get("msg", "")).removeprefix("Value error, "),
        }
        for e in exc.errors()
    ]
    first = errors[0]["message"] if errors else "Invalid input."
    return JSONResponse(
        status_code=422, content={"detail": first, "code": "validation_error", "errors": errors}
    )


def create_app() -> FastAPI:
    _configure_logging()
    app = FastAPI(
        title="PropCheck Nigeria API",
        version="0.1.0",
        description="Verify the property and agent before you pay rent. Payments run in Paystack TEST mode only.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)

    for module in (
        auth, properties, agents, verification, inspections, house_search,
        reservations, reports, reviewer, nearby, files, reference,
    ):  # fmt: skip
        app.include_router(module.router)

    # Public photos only. Private documents live in a different directory and are never mounted.
    app.mount("/media", StaticFiles(directory=storage.public_dir()), name="media")

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
