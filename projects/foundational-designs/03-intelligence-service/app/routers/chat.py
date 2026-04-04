"""
Chat Router — LLM Proxy with Streaming Support

The simplest possible intelligence feature: Rails sends a conversation,
this service calls an LLM, returns the response. Even this trivial feature
benefits from the microservice approach:
  - Rails doesn't need LLM SDKs or API keys
  - You can swap models without redeploying Rails
  - Rate limiting, caching, and fallbacks live in one place
  - Usage tracking and cost attribution are centralized
"""

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sse_starlette.sse import EventSourceResponse

from app.models import ChatRequest, ChatResponse, Message
from app.services.llm_factory import get_model, get_model_info

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Helper: convert our Pydantic Message list to LangChain message objects.
# LangChain uses typed message classes; our API uses role strings.
# ---------------------------------------------------------------------------

def _to_langchain_messages(messages: list[Message]) -> list:
    """Convert API Message objects to LangChain message types.

    LangChain needs typed message objects (SystemMessage, HumanMessage,
    AIMessage) rather than plain dicts. This mapping is straightforward
    but must happen at the boundary.
    """
    lc_messages = []
    for msg in messages:
        if msg.role == "system":
            lc_messages.append(SystemMessage(content=msg.content))
        elif msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages


# ---------------------------------------------------------------------------
# POST /api/chat — Synchronous chat completion
#
# The simple case: send messages, wait for the full response. Good for
# background jobs, internal tools, and any case where you don't need to
# show incremental output.
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Synchronous chat completion.

    Sends the conversation to the configured LLM and waits for the complete
    response. Returns the full text plus metadata about which model was used.
    """
    try:
        model = get_model(request.feature)
        model_info = get_model_info(request.feature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))

    lc_messages = _to_langchain_messages(request.messages)

    try:
        response = await model.ainvoke(lc_messages)
    except Exception as e:
        # Provider failures (rate limits, auth errors, network issues) get
        # a 502 because the upstream service failed, not our code.
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider error: {e}. Check API keys and provider status.",
        )

    # Extract usage info if the provider returned it
    usage = None
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = dict(response.usage_metadata)

    return ChatResponse(
        content=response.content,
        model_used=model_info,
        usage=usage,
    )


# ---------------------------------------------------------------------------
# POST /api/chat/stream — Server-Sent Events (SSE) streaming
#
# SSE streaming is essential for chat UIs. Without it, the user stares at a
# spinner for 5-15 seconds while the LLM generates the full response. With
# SSE, the first token arrives in ~200ms and tokens stream in as they're
# generated — the UI feels alive.
#
# How SSE works:
#   1. Client sends a normal POST request
#   2. Server responds with Content-Type: text/event-stream
#   3. Server sends "data: {...}\n\n" for each chunk
#   4. Client reads chunks as they arrive (EventSource API in JS)
#   5. Server sends a final event and closes the connection
#
# Rails can consume this with an HTTP client that supports streaming
# (e.g., Faraday with a streaming adapter, or Net::HTTP with read_body).
# ---------------------------------------------------------------------------

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat completion via Server-Sent Events (SSE).

    Returns an event stream where each event contains a token. The client
    reads tokens as they arrive and appends them to the display. The final
    event includes a `done: true` flag and model metadata.
    """
    try:
        model = get_model(request.feature)
        model_info = get_model_info(request.feature)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))

    lc_messages = _to_langchain_messages(request.messages)

    async def event_generator() -> AsyncGenerator[str, None]:
        """Yields SSE-formatted events for each token from the LLM.

        Each event is a JSON string. The client parses each event and
        appends the token to the response being displayed.
        """
        try:
            async for chunk in model.astream(lc_messages):
                # Each chunk contains a piece of the response.
                # chunk.content is the text delta for this token.
                if chunk.content:
                    yield json.dumps({"token": chunk.content})

            # Final event signals completion and includes metadata
            yield json.dumps({"done": True, "model_used": model_info})

        except Exception as e:
            # Stream errors get sent as an error event so the client
            # can display a message rather than hanging.
            yield json.dumps({
                "error": f"LLM provider error: {e}",
                "done": True,
            })

    return EventSourceResponse(event_generator())
