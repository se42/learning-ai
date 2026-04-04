"""
API Contracts (Pydantic Models)

These models define the contract between the Rails app and this service.
Rails sends typed requests, gets typed responses. The contract is stable
even when we swap models or change implementations behind the scenes.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class Message(BaseModel):
    """A single message in a conversation.

    Uses the OpenAI role convention (system/user/assistant) because it's
    become the de facto standard across providers. LangChain translates
    these to provider-specific formats automatically.
    """

    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request body for the chat endpoints.

    The `feature` field defaults to "chat" but can be overridden if you want
    to route through a different model config (e.g., a cheaper model for
    internal testing).
    """

    messages: list[Message]
    feature: str = Field(default="chat", description="Feature config to use for model selection")


class ChatResponse(BaseModel):
    """Response from the chat endpoints.

    Always includes `model_used` so the caller can log which model handled
    the request — useful for debugging and cost tracking.
    """

    content: str
    model_used: str
    usage: dict | None = Field(default=None, description="Token usage stats if available")


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Request body for the search endpoint."""

    query: str
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results to return")


class SearchResult(BaseModel):
    """A single search result with relevance score."""

    title: str
    content: str
    score: float = Field(description="Relevance score (higher is better)")
    article_id: str


class SearchResponse(BaseModel):
    """Response from the search endpoint."""

    results: list[SearchResult]
    query: str
    model_used: str


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


class ExtractionRequest(BaseModel):
    """Request body for the structured extraction endpoint.

    `schema_hint` is a natural language description of what to extract.
    Examples:
      - "Extract contact information: name, email, phone"
      - "Extract action items: description, assignee, due_date"
      - "Classify this support case: category, urgency (low/medium/high), summary"
    """

    text: str
    schema_hint: str = Field(description="Natural language description of what to extract")
    feature: str = Field(default="extraction", description="Feature config to use for model selection")


class ExtractionResponse(BaseModel):
    """Response from the extraction endpoint.

    The `extracted` dict contains whatever fields the LLM pulled from the
    text, shaped by the schema_hint. The caller should validate the fields
    they care about — the LLM may include extras or omit optional fields.
    """

    extracted: dict
    model_used: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response from the health check endpoint.

    Lists available features so callers can discover what the service offers.
    """

    status: str
    available_features: list[str]
