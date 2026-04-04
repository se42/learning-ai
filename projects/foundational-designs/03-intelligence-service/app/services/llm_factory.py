"""
LLM Factory — Provider-Agnostic Model Instantiation

Uses LangChain's init_chat_model() to create the right provider's client
based on our feature config. The calling code never knows or cares whether
it's talking to OpenAI, Gemini, or Anthropic — it just gets a BaseChatModel.

This is the core abstraction that makes the service provider-agnostic.
"""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.config import get_feature_config


def get_model(feature: str) -> BaseChatModel:
    """Create an LLM client for the given feature.

    This is the key function in the whole service. It:
      1. Looks up which provider/model to use for this feature (config.py)
      2. Calls init_chat_model() to create the right provider's client
      3. Returns a BaseChatModel that the caller uses without knowing the provider

    init_chat_model() is the magic here — it's LangChain's universal constructor.
    Pass it a provider name and model name, and it returns the right client class
    (ChatOpenAI, ChatGoogleGenerativeAI, etc.) already configured. This means
    swapping from OpenAI to Gemini is a config change, not a code change.

    Args:
        feature: The feature name (e.g., "chat", "search", "extraction").

    Returns:
        A configured BaseChatModel ready to invoke.

    Raises:
        ValueError: If the feature is not recognized.
        ImportError: If the required provider package is not installed.
    """
    config = get_feature_config(feature)

    try:
        model = init_chat_model(
            model=config.model,
            model_provider=config.provider,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    except ImportError as e:
        # This happens when the provider package isn't installed.
        # e.g., you configured a feature to use "anthropic" but haven't
        # installed langchain-anthropic.
        raise ImportError(
            f"Provider package for '{config.provider}' is not installed. "
            f"Install it with: pip install langchain-{config.provider}\n"
            f"Original error: {e}"
        ) from e

    return model


def get_model_info(feature: str) -> str:
    """Return a human-readable string identifying the model for a feature.

    Used for logging and response metadata. Returns a string like
    "openai/gpt-4o" so you can see at a glance which provider and model
    handled a request.

    Args:
        feature: The feature name.

    Returns:
        A string in the format "provider/model".
    """
    config = get_feature_config(feature)
    return f"{config.provider}/{config.model}"
