import json

import pytest

from src.llm.parse import parse_model_output

SUPPORTED = {
    "title": "t",
    "description": "d",
    "evidence_status": "supported",
    "confidence": "medium",
    "citations": [{"page": 3, "quote": "some exact words from the page"}],
    "explanation": "e",
}
INSUFFICIENT = {
    "title": "t2",
    "description": "d2",
    "evidence_status": "insufficient_data",
    "confidence": None,
    "citations": [],
    "explanation": "e2",
}


def answer(*insights: dict) -> str:
    return json.dumps({"insights": list(insights)})


def test_plain_json_is_parsed() -> None:
    parsed = parse_model_output(answer(SUPPORTED, INSUFFICIENT))

    assert [i.title for i in parsed.insights] == ["t", "t2"]
    assert parsed.errors == []
    assert parsed.insights[0].citations[0].page == 3
    assert parsed.insights[1].confidence is None


def test_json_inside_a_markdown_fence_is_parsed() -> None:
    text = "```json\n" + answer(SUPPORTED) + "\n```"

    assert len(parse_model_output(text).insights) == 1


def test_json_with_text_before_and_after_is_parsed() -> None:
    text = "Here is the result:\n" + answer(SUPPORTED) + "\nHope it helps."

    assert len(parse_model_output(text).insights) == 1


@pytest.mark.parametrize("text", ["", "no json here", "[1, 2, 3]", '{"a": '])
def test_text_without_a_json_object_raises(text: str) -> None:
    with pytest.raises(ValueError, match="JSON object"):
        parse_model_output(text)


def test_object_without_insights_list_raises() -> None:
    with pytest.raises(ValueError, match="insights"):
        parse_model_output('{"result": []}')

    with pytest.raises(ValueError, match="insights"):
        parse_model_output('{"insights": "none"}')


def test_empty_insights_list_is_not_an_error_here() -> None:
    parsed = parse_model_output('{"insights": []}')

    assert parsed.insights == []
    assert parsed.errors == []


def test_one_malformed_insight_does_not_drop_the_others() -> None:
    broken = {**SUPPORTED, "evidence_status": "maybe"}
    parsed = parse_model_output(answer(SUPPORTED, broken, INSUFFICIENT))

    assert [i.title for i in parsed.insights] == ["t", "t2"]
    assert len(parsed.errors) == 1
    assert parsed.errors[0].startswith("Insight #2:")
    assert "evidence_status" in parsed.errors[0]


def test_citation_with_page_zero_or_missing_page_is_an_error() -> None:
    zero = {**SUPPORTED, "citations": [{"page": 0, "quote": "q"}]}
    no_page = {**SUPPORTED, "citations": [{"quote": "q"}]}
    parsed = parse_model_output(answer(zero, no_page))

    assert parsed.insights == []
    assert len(parsed.errors) == 2


def test_missing_required_field_is_an_error() -> None:
    without_title = {k: v for k, v in SUPPORTED.items() if k != "title"}
    parsed = parse_model_output(answer(without_title))

    assert parsed.insights == []
    assert "title" in parsed.errors[0]


def test_confidence_and_citations_are_optional() -> None:
    minimal = {
        "title": "t",
        "description": "d",
        "evidence_status": "insufficient_data",
        "explanation": "e",
    }
    parsed = parse_model_output(answer(minimal))

    assert parsed.insights[0].confidence is None
    assert parsed.insights[0].citations == []


def test_doi_and_psi_id_written_by_the_model_are_ignored() -> None:
    sneaky = {
        **SUPPORTED,
        "doi": "10.0/fake",
        "citations": [
            {
                "page": 3,
                "quote": "q",
                "doi": "10.0/fake",
                "psi_id": "PSI-999",
            }
        ],
    }
    insight = parse_model_output(answer(sneaky)).insights[0]

    assert not hasattr(insight, "doi")
    assert not hasattr(insight.citations[0], "doi")
    assert not hasattr(insight.citations[0], "psi_id")
