from dataclasses import dataclass, field

from pydantic import ValidationError

from src.catalog import get_doi
from src.llm.parse import RawInsight
from src.llm.schemas import Citation, Insight
from src.llm.verify import verify_citation


@dataclass(frozen=True)
class Rejection:
    """An insight that did not reach the dashboard, and why."""

    psi_id: str
    title: str
    reasons: list[str]
    insight: dict


@dataclass(frozen=True)
class AssembleResult:
    """Accepted insights, rejected ones and non-fatal warnings."""

    insights: list[Insight] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _citation_problems(
    raw: RawInsight,
    extracted_doc: dict,
    psi_id: str,
    min_quote_words: int,
) -> list[str]:
    """Return one reason per citation that is too short or not verifiable."""
    problems = []

    for citation in raw.citations:
        words = len(citation.quote.split())

        if words < min_quote_words:
            problems.append(
                f"Citation on page {citation.page}: the quote has {words} "
                f"words; at least {min_quote_words} are required."
            )
            continue

        result = verify_citation(
            Citation(psi_id=psi_id, page=citation.page, quote=citation.quote),
            extracted_doc,
        )

        if not result.ok:
            problems.append(f"Citation on page {citation.page}: {result.reason}")

    return problems


def _build_insight(raw: RawInsight, psi_id: str, doi: str | None) -> Insight:
    """Build the official Insight (validated by schemas.py) from a raw one."""
    return Insight(
        title=raw.title,
        description=raw.description,
        evidence_status=raw.evidence_status,
        confidence=raw.confidence,
        citations=[
            Citation(
                psi_id=psi_id,
                doi=doi,
                page=citation.page,
                quote=citation.quote,
            )
            for citation in raw.citations
        ],
        explanation=raw.explanation,
    )


def assemble_insights(
    raw_insights: list[RawInsight],
    extracted_doc: dict,
    catalog: dict[str, str],
    min_quote_words: int,
) -> AssembleResult:
    """Verify raw insights and turn the good ones into official Insights.

    The psi_id comes from the extracted document and the DOI from the
    catalog; the model never writes them. An insight is rejected, as a whole,
    if any citation is shorter than min_quote_words words or is not found on
    its page, or if the official schema does not accept it. A missing DOI is
    only a warning. Raises ValueError if the document is malformed.
    """
    psi_id = extracted_doc.get("psi_id") if isinstance(extracted_doc, dict) else None

    if not isinstance(psi_id, str) or not psi_id.strip():
        raise ValueError("The extracted document has no 'psi_id'.")

    doi = get_doi(psi_id, catalog)
    warnings = [] if doi else [f"No DOI in the catalog for {psi_id}."]
    accepted: list[Insight] = []
    rejected: list[Rejection] = []

    for raw in raw_insights:
        reasons = _citation_problems(raw, extracted_doc, psi_id, min_quote_words)

        if not reasons:
            try:
                accepted.append(_build_insight(raw, psi_id, doi))
                continue
            except ValidationError as error:
                reasons = [
                    f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                    if item["loc"]
                    else item["msg"]
                    for item in error.errors()
                ]

        rejected.append(
            Rejection(
                psi_id=psi_id,
                title=raw.title,
                reasons=reasons,
                insight=raw.model_dump(),
            )
        )

    return AssembleResult(accepted, rejected, warnings)
