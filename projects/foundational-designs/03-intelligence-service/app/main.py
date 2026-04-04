"""
Intelligence Service — Internal AI Microservice

A FastAPI service that provides AI capabilities to the Rails application.
Rails calls this over HTTP; this service handles LLM provider management,
model selection, and response formatting.

This is the foundation for more complex capabilities:
  - Phase 1 (now): Stateless LLM proxy, search, extraction
  - Phase 2: Conversation memory, RAG with vector stores
  - Phase 3: Multi-step agents, tool use, checkpointing
  - Phase 4: User-authorized operations, delegated credentials
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import FEATURE_MODEL_MAP
from app.models import HealthResponse
from app.routers import chat, extract, search

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("intelligence-service")


# ---------------------------------------------------------------------------
# Lifespan — runs on startup and shutdown
#
# We use the modern lifespan pattern instead of the deprecated @app.on_event.
# This logs the configuration summary so you can verify at a glance which
# models are mapped to which features.
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log configuration summary on startup."""
    logger.info("Intelligence Service starting up")
    logger.info("Feature-to-model mapping:")
    for feature, config in FEATURE_MODEL_MAP.items():
        logger.info(f"  {feature}: {config.provider}/{config.model} "
                     f"(temp={config.temperature}, max_tokens={config.max_tokens})")
    logger.info("Ready to serve requests")

    yield  # Application runs here

    logger.info("Intelligence Service shutting down")


# ---------------------------------------------------------------------------
# Application
#
# In production, you'd also add:
#   - Request logging middleware (log every request with timing)
#   - Error tracking (Sentry, Datadog, etc.)
#   - Rate limiting (slowapi or a reverse proxy)
#   - Request ID propagation (for tracing across Rails -> this service)
#   - Authentication middleware (API key or JWT validation)
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Intelligence Service",
    description=(
        "Internal AI microservice for the Rails application. "
        "Provides chat, search, and structured extraction capabilities. "
        "Rails says what to do; this service decides how."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware — allow all origins for this demo.
# In production, lock this down to your Rails app's domain(s):
#   allow_origins=["https://app.acme.com", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Mount routers
# ---------------------------------------------------------------------------

app.include_router(chat.router)
app.include_router(search.router)
app.include_router(extract.router)


# ---------------------------------------------------------------------------
# Health check
#
# Every microservice needs a health endpoint. This one also advertises
# available features, which is useful for service discovery and monitoring.
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint.

    Returns the service status and a list of available features.
    Use this for load balancer health checks and service discovery.
    """
    return HealthResponse(
        status="ok",
        available_features=sorted(FEATURE_MODEL_MAP.keys()),
    )
