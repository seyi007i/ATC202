"""FastAPI application entry point for SafeBank Companion."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from app.agent_loop import AgentLoop
from app.dependencies import get_agent_loop
from app.models import (
    AnthropicAPIError,
    AnthropicConnectionError,
    AnthropicTemporaryError,
    AnthropicTimeoutError,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    EscalationWriteError,
    InvalidInputError,
    MalformedAgentOutputError,
    MissingAPIKeyError,
    SafeBankError,
)

logger = logging.getLogger("safebank")

_UPSTREAM_ERRORS = (
    AnthropicTimeoutError,
    AnthropicConnectionError,
    AnthropicTemporaryError,
    AnthropicAPIError,
    MalformedAgentOutputError,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Fail fast with a friendly message if the API key is missing."""
    try:
        config.require_api_key()
    except MissingAPIKeyError as exc:
        logger.error(str(exc))
        sys.exit(1)
    yield


app = FastAPI(title="SafeBank Companion", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler so no unexpected error ever leaks a stack trace."""
    logger.exception("Unhandled error while processing %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(detail="Something went wrong. Please try again.").model_dump(),
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the home page."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request) -> HTMLResponse:
    """Render the chat page."""
    return templates.TemplateResponse(request, "chat.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    loop: AgentLoop = Depends(get_agent_loop),
) -> ChatResponse:
    """Process one chat turn and return SafeBank Companion's reply.

    Args:
        payload: The validated chat request body.
        loop: The injected agent loop.

    Returns:
        The assistant's structured response.

    Raises:
        HTTPException: 400 on invalid input, 502 on upstream API
            failure, 500 on any other unexpected error.
    """
    try:
        return loop.run_turn(payload.session_id, payload.message)
    except InvalidInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except _UPSTREAM_ERRORS as exc:
        logger.warning("Upstream Anthropic failure: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=(
                "SafeBank Companion couldn't reach the AI service right now. "
                "Please try again in a moment."
            ),
        ) from exc
    except EscalationWriteError as exc:
        logger.warning("Escalation write failure: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=(
                "Your message was analyzed, but we couldn't record the "
                "escalation. Please contact your bank directly if this is urgent."
            ),
        ) from exc
    except SafeBankError as exc:
        logger.exception("Unexpected SafeBank error")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.") from exc
