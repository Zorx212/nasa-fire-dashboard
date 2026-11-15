import json

import pytest

from src.config import MAX_INSIGHTS_PER_DOC, MIN_QUOTE_WORDS
from src.llm.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_message
from src.paths import TEXT_DIR

PSI_107_JSON = TEXT_DIR / "PSI-107" / "PSI-107-SPICE-FinalReport.json"


@pytest.fixture(scope="module")
def psi107() -> dict:
    return json.loads(PSI_107_JSON.read_text(encoding="utf-8"))


def test_prompt_version_is_a_semantic_version_string() -> None:
    parts = PROMPT_VERSION.split(".")

    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_system_prompt_states_the_configured_limits() -> None:
    assert f"at most {MAX_INSIGHTS_PER_DOC} insights" in SYSTEM_PROMPT
    assert f"at least {MIN_QUOTE_WORDS} words" in SYSTEM_PROMPT


def test_system_prompt_does_not_ask_the_model_for_doi_or_psi_id() -> None:
    assert '"doi"' not in SYSTEM_PROMPT
    assert '"psi_id"' not in SYSTEM_PROMPT
    assert "Do not write a DOI" in SYSTEM_PROMPT


def test_system_prompt_example_has_the_fields_the_parser_reads() -> None:
    for field in (
        '"title"',
        '"description"',
        '"evidence_status"',
        '"confidence"',
        '"citations"',
        '"page"',
        '"quote"',
        '"explanation"',
        '"supported"',
        '"insufficient_data"',
    ):
        assert field in SYSTEM_PROMPT


def test_user_message_marks_every_page_of_the_real_document(psi107) -> None:
    message = build_user_message(psi107)

    for page in psi107["pages"]:
        assert f"[PAGE {page['page_number']}]" in message

    assert "PSI-107" in message
    assert message.rstrip().endswith("Return the JSON object now.")


def test_user_message_sends_the_raw_page_text(psi107) -> None:
    page_10 = next(p for p in psi107["pages"] if p["page_number"] == 10)

    assert page_10["text"] in build_user_message(psi107)


def test_empty_pages_are_skipped() -> None:
    doc = {
        "psi_id": "PSI-000",
        "filename": "PSI-000-test.pdf",
        "pages": [
            {"page_number": 1, "text": "first page", "is_empty": False},
            {"page_number": 2, "text": "  \n", "is_empty": True},
            {"page_number": 3, "text": "third page", "is_empty": False},
        ],
    }
    message = build_user_message(doc)

    assert "[PAGE 1]" in message
    assert "[PAGE 2]" not in message
    assert "[PAGE 3]" in message


def test_malformed_documents_raise_clear_errors() -> None:
    with pytest.raises(ValueError, match="dict"):
        build_user_message(["not a dict"])

    with pytest.raises(ValueError, match="pages"):
        build_user_message({"psi_id": "PSI-000"})


def test_the_prompt_example_is_a_valid_answer_that_follows_its_own_rules() -> None:
    from src.llm.parse import parse_model_output
    from src.llm.prompts import _OUTPUT_EXAMPLE

    parsed = parse_model_output(_OUTPUT_EXAMPLE)

    assert parsed.errors == []
    assert [i.evidence_status for i in parsed.insights] == [
        "supported",
        "insufficient_data",
    ]

    for insight in parsed.insights:
        for citation in insight.citations:
            assert len(citation.quote.split()) >= MIN_QUOTE_WORDS


def test_changing_the_prompt_text_requires_a_new_prompt_version() -> None:
    import hashlib

    # If this fails you changed SYSTEM_PROMPT: bump PROMPT_VERSION in
    # src/llm/prompts.py (the cache key changes with the text) and then
    # update this hash and the version below.
    digest = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()

    assert (PROMPT_VERSION, digest) == (
        "1.0.0",
        "6178720fc8e02e4e17c2a8356890a19e2d1b6fa951d5d129850973252d0c3a06",
    )


@pytest.mark.parametrize(
    "page",
    [
        "not a dict",
        {"text": "no number"},
        {"page_number": 1},
        {"page_number": "1", "text": "number as text"},
        {"page_number": 1, "text": 5},
    ],
)
def test_malformed_page_raises_a_clear_error(page) -> None:
    with pytest.raises(ValueError, match="page_number"):
        build_user_message({"psi_id": "PSI-000", "pages": [page]})
