from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routers import auth, chat, conversations, health, speech
from app.api.routers.admin import (
    accreditations_router,
    academic_overview_router,
    cycle_overview_router,
    elements_router,
    formations_router,
    orientation_matrix_router,
    orientation_rules_router,
    parcours_router,
    rag_router,
    specialisations_router,
    tarifs_router,
)
from app.core.config import get_settings, validate_runtime_settings
from app.core.exceptions import AppError, AuthenticationError, RateLimitError
from app.core.logging import configure_logging
from app.core.middleware import (
    RequestIdMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.infrastructure.chroma import AsyncChromaRepository
from app.infrastructure.db import close_database
from app.infrastructure.inference import HttpInferenceClient, HttpSpeechClient
from app.infrastructure.redis import close_redis, get_redis


logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    validate_runtime_settings(settings)
    configure_logging(settings)
    application.state.inference = HttpInferenceClient(settings)
    application.state.speech_inference = HttpSpeechClient(settings)
    application.state.chroma = AsyncChromaRepository(settings)
    try:
        yield
    finally:
        await application.state.inference.close()
        await application.state.speech_inference.close()
        await close_database()
        await close_redis()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Assistant conversationnel académique IIT",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Idempotency-Key",
        "X-CSRF-Token",
        "X-Request-ID",
    ],
    expose_headers=["X-Request-ID", "Retry-After"],
    max_age=600,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=settings.max_request_bytes,
    path_limits={
        f"{settings.api_v1_prefix}/speech/transcribe": (
            settings.speech_max_upload_bytes + settings.max_request_bytes
        ),
    },
)
app.add_middleware(RequestIdMiddleware)


def _request_id(request: Request) -> str | None:
    value = request.scope.get("request_id")
    return str(value) if value else None


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    headers: dict[str, str] = {}
    if isinstance(exc, AuthenticationError):
        headers["WWW-Authenticate"] = "Bearer"
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.details["retry_after"])
    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": _request_id(request),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    issues = [
        {
            "field": ".".join(str(part) for part in issue["loc"] if part != "body"),
            "message": issue["msg"],
            "type": issue["type"],
        }
        for issue in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "La requête contient des données invalides.",
                "details": {"issues": issues},
                "request_id": _request_id(request),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Requête refusée."
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": message,
                "details": {},
                "request_id": _request_id(request),
            }
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "UNHANDLED_REQUEST_ERROR",
        extra={
            "request_id": _request_id(request),
            "event_fields": {"method": request.method, "path": request.url.path},
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Une erreur interne est survenue.",
                "details": {},
                "request_id": _request_id(request),
            }
        },
    )


app.include_router(health.router)
for api_router in (
    auth.router,
    chat.router,
    conversations.router,
    speech.router,
    academic_overview_router,
    cycle_overview_router,
    parcours_router,
    formations_router,
    orientation_matrix_router,
    specialisations_router,
    elements_router,
    tarifs_router,
    orientation_rules_router,
    accreditations_router,
    rag_router,
):
    app.include_router(api_router, prefix=settings.api_v1_prefix)
