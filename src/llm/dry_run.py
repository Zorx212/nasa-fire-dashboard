import math
from dataclasses import dataclass
from pathlib import Path

from src.config import ESTIMATED_CHARS_PER_TOKEN
from src.llm.client import is_cached
from src.llm.prompts import SYSTEM_PROMPT, build_user_message


@dataclass(frozen=True)
class RequestPreview:
    """What one document would send to the model, without sending it."""

    psi_id: str
    filename: str
    pages_sent: int
    pages_skipped: int
    characters: int
    estimated_input_tokens: int
    cached: bool


def preview_request(
    extracted_doc: dict,
    model: str,
    max_tokens: int,
    cache_dir: Path,
) -> RequestPreview:
    """Describe the request for one extracted document. Calls nothing.

    Page blocks are the [PAGE n] blocks of the user message; empty pages are
    skipped. The token count is an estimate (characters divided by
    ESTIMATED_CHARS_PER_TOKEN), not the tokenizer's. Raises ValueError, like
    build_user_message, if the document has the wrong shape.
    """
    user_message = build_user_message(extracted_doc)
    pages = extracted_doc["pages"]
    skipped = sum(1 for page in pages if page.get("is_empty"))
    characters = len(SYSTEM_PROMPT) + len(user_message)

    return RequestPreview(
        psi_id=extracted_doc.get("psi_id", "<unknown>"),
        filename=extracted_doc.get("filename", "<unknown file>"),
        pages_sent=len(pages) - skipped,
        pages_skipped=skipped,
        characters=characters,
        estimated_input_tokens=math.ceil(
            characters / ESTIMATED_CHARS_PER_TOKEN
        ),
        cached=is_cached(
            SYSTEM_PROMPT,
            user_message,
            model=model,
            max_tokens=max_tokens,
            cache_dir=cache_dir,
        ),
    )


def format_preview(preview: RequestPreview) -> str:
    """One readable line for a preview."""
    outcome = (
        "cache hit (free)"
        if preview.cached
        else "cache miss (would call the paid API)"
    )

    return (
        f"{preview.psi_id} {preview.filename}: "
        f"{preview.pages_sent} page block(s) sent, "
        f"{preview.pages_skipped} empty skipped, "
        f"{preview.characters} characters, "
        f"about {preview.estimated_input_tokens} input tokens (estimate), "
        f"{outcome}"
    )
