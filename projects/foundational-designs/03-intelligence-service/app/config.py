"""
Feature-to-Model Configuration

This is the key architectural boundary: the Rails app requests a *capability*
(chat, search, extraction), and this service decides which model serves it.

This separation lets the AI team:
  - Swap models without redeploying Rails
  - A/B test models per feature
  - Use cheaper models for simple tasks, stronger models for complex ones
  - Handle provider outages by rerouting to alternatives
"""

import os
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration for a single feature's LLM backend.

    Each feature in the service maps to one of these. The Rails app never
    sees this — it just says "do chat" or "do extraction" and we pick the
    right model behind the scenes.
    """

    provider: str  # LangChain provider name: "openai", "google-genai", etc.
    model: str  # Model identifier within that provider
    temperature: float  # 0.0 = deterministic, 1.0 = creative
    max_tokens: int  # Maximum response length


# ---------------------------------------------------------------------------
# Feature-to-Model Mapping
#
# This is the single source of truth for which model handles which feature.
# Change a line here, restart the service, and every Rails request for that
# feature now uses the new model. No Rails deploy required.
# ---------------------------------------------------------------------------

FEATURE_MODEL_MAP: dict[str, ModelConfig] = {
    # Chat: uses GPT-4o for high-quality conversational responses.
    # Temperature 0.7 gives creative but coherent answers. This is the
    # "flagship" feature so we use the strongest model.
    "chat": ModelConfig(
        provider="openai",
        model="gpt-4o",
        temperature=0.7,
        max_tokens=2048,
    ),
    # Search: uses Gemini 2.0 Flash for speed. Search reranking needs to be
    # fast (users are waiting for results), and the task is simpler than open
    # conversation. Low temperature because we want consistent ranking, not
    # creative interpretation of queries.
    "search": ModelConfig(
        provider="google-genai",
        model="gemini-2.0-flash",
        temperature=0.1,
        max_tokens=1024,
    ),
    # Extraction: uses GPT-4o-mini for structured output. Extraction is a
    # constrained task (pull fields from text), so a smaller/cheaper model
    # works great. Temperature 0.0 because we want deterministic extraction —
    # the same email should always produce the same contact info.
    "extraction": ModelConfig(
        provider="openai",
        model="gpt-4o-mini",
        temperature=0.0,
        max_tokens=1024,
    ),
}


# ---------------------------------------------------------------------------
# API Keys — loaded from environment variables
#
# The service needs keys for each provider it talks to. In production these
# come from a secrets manager; for local dev, use a .env file or export them.
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")


def get_feature_config(feature: str) -> ModelConfig:
    """Look up the model configuration for a given feature.

    Args:
        feature: The feature name (e.g., "chat", "search", "extraction").

    Returns:
        The ModelConfig for that feature.

    Raises:
        ValueError: If the feature is not recognized. The error message lists
            all available features so the caller can fix the request.
    """
    if feature not in FEATURE_MODEL_MAP:
        available = ", ".join(sorted(FEATURE_MODEL_MAP.keys()))
        raise ValueError(
            f"Unknown feature '{feature}'. "
            f"Available features: {available}"
        )
    return FEATURE_MODEL_MAP[feature]
