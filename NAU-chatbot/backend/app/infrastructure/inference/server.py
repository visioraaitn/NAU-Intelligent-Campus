from __future__ import annotations

import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

from app.core.config import get_settings, validate_inference_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.infrastructure.inference.model_manager import ModelManager
from app.infrastructure.inference.schemas import (
    EmbedRequest,
    EmbedResponse,
    GenerateRequest,
    GenerateResponse,
    RerankRequest,
    RerankResponse,
)
from app.services.llm.providers import LLMMessage


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    validate_inference_settings(settings)
    configure_logging(settings)
    manager = ModelManager()
    app.state.models = manager
    app.state.load_error = None
    try:
        await manager.load()
    except Exception as exc:
        app.state.load_error = type(exc).__name__
        logger.exception("INFERENCE_MODEL_LOAD_FAILED")
    yield


app = FastAPI(
    title="IIT Internal Inference",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_048_576)


def authorize(x_inference_token: str = Header(default="")) -> None:
    expected = get_settings().inference_service_token.get_secret_value()
    if not expected or not hmac.compare_digest(x_inference_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


def manager(request: Request) -> ModelManager:
    return request.app.state.models


@app.get("/health")
async def health(request: Request) -> dict[str, object]:
    models: ModelManager = request.app.state.models
    return {"ready": models.ready, "error": request.app.state.load_error}


@app.post("/v1/generate", response_model=GenerateResponse, dependencies=[Depends(authorize)])
async def generate(payload: GenerateRequest, models: ModelManager = Depends(manager)) -> GenerateResponse:
    text = await models.generate(
        payload.role,
        tuple(LLMMessage(item.role, item.content) for item in payload.messages),
        payload.max_new_tokens,
    )
    return GenerateResponse(text=text)


@app.post("/v1/embed", response_model=EmbedResponse, dependencies=[Depends(authorize)])
async def embed(payload: EmbedRequest, models: ModelManager = Depends(manager)) -> EmbedResponse:
    return EmbedResponse(embeddings=await models.embed(payload.texts, query=payload.query))


@app.post("/v1/rerank", response_model=RerankResponse, dependencies=[Depends(authorize)])
async def rerank(payload: RerankRequest, models: ModelManager = Depends(manager)) -> RerankResponse:
    return RerankResponse(scores=await models.rerank(payload.query, payload.documents))
