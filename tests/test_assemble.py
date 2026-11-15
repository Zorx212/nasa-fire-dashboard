import json
from datetime import datetime, timezone

import pytest

from src.llm.assemble import assemble_insights
from src.llm.parse import RawCitation, RawInsight
from src.llm.schemas import InsightsDocument
from src.paths import TEXT_DIR

PSI_107_JSON = TEXT_DIR / "PSI-107" / "PSI-107-SPICE-FinalReport.json"
CATALOG = {"PSI-107": "10.1234/spice"}

# Real text of PSI-107 (page 10 and page 2).
GLOVEBOX_QUOTE = (
    "Inside the Glovebox, the core of the apparatus is the Experimental "
    "Assembly which consists of a flow duct and its accessories."
)
SMOKE_QUOTE = "smoke points in non-buoyant laminar jet diffusion flames"


@pytest.fixture(scope="module")
def psi107() -> dict:
    return json.loads(PSI_107_JSON.read_text(encoding="utf-8"))


def supported(*citations: tuple[int, str], **overrides) -> RawInsight:
    data = {
        "title": "Apparatus",
        "description": "d",
        "evidence_status": "supported",
        "confidence": "medium",
        "citations": [RawCitation(page=p, quote=q) for p, q in citations],
        "explanation": "e",
    }
    data.update(overrides)

    return RawInsight(**data)


def insufficient(**overrides) -> RawInsight:
    data = {
        "title": "Not enough",
        "description": "d",
        "evidence_status": "insufficient_data",
        "confidence": None,
        "citations": [],
        "explanation": "e",
    }
    data.update(overrides)

    return RawInsight(**data)


def run(raw_insights, doc, catalog=CATALOG, min_words=8):
    return assemble_insights(raw_insights, doc, catalog, min_words)


def test_real_quote_is_accepted_with_psi_id_and_doi_from_code(psi107) -> None:
    result = run([supported((10, GLOVEBOX_QUOTE))], psi107)

    assert result.rejected == []
    assert result.warnings == []
    citation = result.insights[0].citations[0]
    assert citation.psi_id == "PSI-107"
    assert citation.doi == "10.1234/spice"
    assert citation.page == 10
    assert citation.quote == GLOVEBOX_QUOTE


def test_invented_quote_is_rejected_with_the_reason(psi107) -> None:
    quote = "The flame propagated at 99 cm/s in every single test."
    result = run([supported((10, quote))], psi107)

    assert result.insights == []
    assert result.rejected[0].title == "Apparatus"
    assert "not found" in result.rejected[0].reasons[0]


def test_real_quote_on_the_wrong_page_is_rejected(psi107) -> None:
    result = run([supported((5, GLOVEBOX_QUOTE))], psi107)

    assert result.insights == []
    assert "page 5" in result.rejected[0].reasons[0]


def test_page_out_of_range_is_rejected(psi107) -> None:
    result = run([supported((999, GLOVEBOX_QUOTE))], psi107)

    assert "does not exist" in result.rejected[0].reasons[0]


def test_short_quote_is_rejected_even_if_it_is_real(psi107) -> None:
    result = run([supported((10, "Inside the Glovebox, the core"))], psi107)

    assert result.insights == []
    assert "at least 8" in result.rejected[0].reasons[0]


def test_min_quote_words_is_a_parameter(psi107) -> None:
    short = supported((10, "Inside the Glovebox, the core"))

    assert run([short], psi107, min_words=5).insights != []
    assert run([short], psi107, min_words=6).insights == []


def test_one_bad_citation_rejects_the_whole_insight(psi107) -> None:
    result = run(
        [supported((10, GLOVEBOX_QUOTE), (10, "an invented sentence with many words in it"))],
        psi107,
    )

    assert result.insights == []
    assert len(result.rejected[0].reasons) == 1


def test_good_and_bad_insights_are_separated_in_order(psi107) -> None:
    good = supported((2, SMOKE_QUOTE), title="Smoke")
    bad = supported((5, GLOVEBOX_QUOTE), title="Bad")
    none = insufficient(title="Nothing")
    result = run([good, bad, none], psi107)

    assert [i.title for i in result.insights] == ["Smoke", "Nothing"]
    assert [r.title for r in result.rejected] == ["Bad"]
    assert result.rejected[0].psi_id == "PSI-107"
    assert result.rejected[0].insight["title"] == "Bad"


def test_insufficient_data_without_citations_is_accepted(psi107) -> None:
    result = run([insufficient()], psi107)

    assert result.insights[0].evidence_status == "insufficient_data"
    assert result.insights[0].citations == []
    assert result.rejected == []


def test_insufficient_data_with_citations_is_rejected_by_the_schema(
    psi107,
) -> None:
    result = run([insufficient(citations=[RawCitation(page=10, quote=GLOVEBOX_QUOTE)])], psi107)

    assert result.insights == []
    assert "must not include citations" in result.rejected[0].reasons[0]


def test_supported_without_citations_or_confidence_is_rejected(psi107) -> None:
    no_citations = supported()
    no_confidence = supported((10, GLOVEBOX_QUOTE), confidence=None)
    result = run([no_citations, no_confidence], psi107)

    assert result.insights == []
    assert "at least one citation" in result.rejected[0].reasons[0]
    assert "confidence" in result.rejected[1].reasons[0]


def test_psi_not_in_catalog_gives_a_warning_and_no_doi(psi107) -> None:
    result = run([supported((10, GLOVEBOX_QUOTE))], psi107, catalog={})

    assert result.insights[0].citations[0].doi is None
    assert result.warnings == ["No DOI in the catalog for PSI-107."]


def test_accepted_insights_fit_the_official_document(psi107) -> None:
    result = run([supported((10, GLOVEBOX_QUOTE)), insufficient()], psi107)
    document = InsightsDocument(
        generated_at=datetime.now(timezone.utc),
        model="m",
        prompt_version="1.0.0",
        insights=result.insights,
    )

    assert len(document.insights) == 2


def test_document_without_psi_id_raises() -> None:
    with pytest.raises(ValueError, match="psi_id"):
        run([insufficient()], {"pages": []})

    with pytest.raises(ValueError, match="psi_id"):
        run([insufficient()], ["not a dict"])


def test_malformed_pages_raise_instead_of_rejecting_silently() -> None:
    doc = {"psi_id": "PSI-000", "filename": "PSI-000-x.pdf"}

    with pytest.raises(ValueError, match="pages"):
        run([supported((1, GLOVEBOX_QUOTE))], doc)
