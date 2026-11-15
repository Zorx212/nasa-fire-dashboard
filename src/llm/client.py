from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from src.config import (
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    get_api_key,
)
from src.llm.cache import (
    build_cache_key,
    get_cached_response,
    save_cached_response,
)
from src.paths import CACHE_DIR

# Only answers that ended normally are worth caching.
_USABLE_STOP_REASONS = ("end_turn", "stop_sequence")


def build_request(
    system: str,
    user_message: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> dict:
    """Build the exact request sent to the API (it is also the cache key)."""
    return {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    }


def _extract_text(response) -> str:
    """Join the text blocks of an API response or raise RuntimeError."""
    text = "".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    )

    if not text.strip():
        raise RuntimeError("The API response has no text.")

    return text


def _call_api(request: dict, sdk_client) -> object:
    """Send the request. The real SDK client (and the key) is created here."""
    if sdk_client is None:
        sdk_client = anthropic.Anthropic(api_key=get_api_key())

    try:
        return sdk_client.messages.create(**request)
    except anthropic.APIError as error:
        raise RuntimeError(
            f"Anthropic API call failed ({type(error).__name__}): {error}. "
            "Check the internet connection and the API key."
        ) from error


def complete(
    system: str,
    user_message: str,
    *,
    model: str = LLM_MODEL,
    max_tokens: int = LLM_MAX_TOKENS,
    temperature: float = LLM_TEMPERATURE,
    cache_dir: Path = CACHE_DIR,
    sdk_client: anthropic.Anthropic | None = None,
    validate: Callable[[str], None] | None = None,
) -> str:
    """Return the model's text for this request, using the cache first.

    A cache hit needs no key and no internet. On a miss it calls the API
    (creating the SDK client, which reads the key, unless sdk_client is
    given), stores the real response in the cache and returns its text.
    Raises RuntimeError if the key is missing, the call fails, the answer
    was cut at max_tokens, stopped for another unusable reason (such as a
    refusal) or has no text. If validate is given it is called with the
    text and may raise (for example ValueError); an answer that fails is
    never cached, so a bad answer cannot become permanent.
    """
    request = build_request(
        system, user_message, model, max_tokens, temperature
    )
    key = build_cache_key(request)
    cached = get_cached_response(key, cache_dir)

    if cached is not None:
        cached_text = cached.get("text")

        if isinstance(cached_text, str) and cached_text.strip():
            return cached_text

    response = _call_api(request, sdk_client)
    stop_reason = getattr(response, "stop_reason", None)

    if stop_reason == "max_tokens":
        raise RuntimeError(
            f"The answer was cut at max_tokens={max_tokens}. "
            "Raise LLM_MAX_TOKENS or ask for fewer insights."
        )

    if stop_reason not in _USABLE_STOP_REASONS:
        raise RuntimeError(
            f"The API stopped with stop_reason={stop_reason!r}, "
            "so the answer is not usable and was not cached."
        )

    text = _extract_text(response)

    if validate is not None:
        validate(text)

    usage = getattr(response, "usage", None)

    save_cached_response(
        key,
        cache_dir,
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "stop_reason": getattr(response, "stop_reason", None),
            "usage": {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            },
            "text": text,
        },
    )

    return text
