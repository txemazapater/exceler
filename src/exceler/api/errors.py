from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from exceler.domain.sources.errors import (
    DomainError,
    SourceConflictError,
    SourceNotFoundError,
    SourceValidationError,
)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SourceNotFoundError)
    async def not_found_handler(_: Request, exc: SourceNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": exc.code, "message": str(exc)}},
        )

    @app.exception_handler(SourceValidationError)
    async def validation_handler(_: Request, exc: SourceValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(SourceConflictError)
    async def conflict_handler(_: Request, exc: SourceConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(DomainError)
    async def domain_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "domain_error", "message": str(exc)}},
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "request_validation_error",
                    "message": "Invalid request",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "conflict", "message": str(exc)}},
        )
