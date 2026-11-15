import json
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class RawCitation(BaseModel):
    """A citation as the model writes it: only the page and the quote."""

    page: int = Field(gt=0)
    quote: str


class RawInsight(BaseModel):
    """An insight as the model writes it, before verification.

    Unknown keys (for example a DOI the model added) are ignored on purpose:
    the final DOI and psi_id come from the catalog and the document.
    """

    title: str
    description: str
    evidence_status: Literal["supported", "insufficient_data"]
    confidence: Literal["high", "medium", "low"] | None = None
    citations: list[RawCitation] = Field(default_factory=list)
    explanation: str


@dataclass(frozen=True)
class ParsedOutput:
    """Insights that parsed, plus one message per insight that did not."""

    insights: list[RawInsight]
    errors: list[str] = field(default_factory=list)


def _load_json_object(text: str) -> dict:
    """Return the JSON object in the model's answer or raise ValueError.

    Accepts plain JSON, JSON inside a markdown code fence and JSON with
    text before or after it.
    """
    candidates = [text.strip()]
    start, end = text.find("{"), text.rfind("}")

    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if isinstance(data, dict):
            return data

    raise ValueError("The model output is not a JSON object.")


def _describe(error: ValidationError) -> str:
    """Summarize a pydantic error as 'field: message' pairs."""
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()
    )


def parse_model_output(text: str) -> ParsedOutput:
    """Parse the model's answer into raw insights.

    Raises ValueError if the answer is not a JSON object with an 'insights'
    list. An insight that does not have the expected shape does not stop the
    others: it is reported in ParsedOutput.errors with its position.
    """
    data = _load_json_object(text)
    raw_insights = data.get("insights")

    if not isinstance(raw_insights, list):
        raise ValueError("The model output has no 'insights' list.")

    insights: list[RawInsight] = []
    errors: list[str] = []

    for position, raw in enumerate(raw_insights, start=1):
        try:
            insights.append(RawInsight.model_validate(raw))
        except ValidationError as error:
            errors.append(f"Insight #{position}: {_describe(error)}")

    return ParsedOutput(insights=insights, errors=errors)
