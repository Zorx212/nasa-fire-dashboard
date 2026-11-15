import json
from pathlib import Path

import pytest

from src.llm.prompts import PROMPT_VERSION
from src.llm.schemas import InsightsDocument
from src.llm_extract import (
    extract_document,
    find_text_files,
    run_extraction,
)
from src.paths import TEXT_DIR

PSI_107_JSON = TEXT_DIR / "PSI-107" / "PSI-107-SPICE-FinalReport.json"
CATALOG = {"PSI-107": "10.1234/spice"}

# Real text of PSI-107 (pages 10 and 2).
GLOVEBOX_QUOTE = (
    "Inside the Glovebox, the core of the apparatus is the Experimental "
    "Assembly which consists of a flow duct and its accessories."
)
SMOKE_QUOTE = "smoke points in non-buoyant laminar jet diffusion flames"


def insight(title: str, citations: list[dict], status="supported") -> dict:
    return {
        "title": title,
        "description": "d",
        "evidence_status": status,
        "confidence": "medium" if status == "supported" else None,
        "citations": citations,
        "explanation": "e",
    }


GOOD = insight("Apparatus", [{"page": 10, "quote": GLOVEBOX_QUOTE}])
INVENTED = insight(
    "Invented",
    [{"page": 10, "quote": "The flame propagated at 99 cm/s in every test run."}],
)
NOTHING = insight("Nothing", [], status="insufficient_data")


class FakeLlm:
    """A fake model: returns a canned answer and records what it was asked."""

    def __init__(self, *insights: dict, raw: str | None = None):
        self.answer = raw if raw is not None else json.dumps({"insights": list(insights)})
        self.calls: list[tuple[str, str]] = []

    def __call__(self, system: str, user: str) -> str:
        self.calls.append((system, user))

        return self.answer


@pytest.fixture()
def text_dir(tmp_path: Path) -> Path:
    folder = tmp_path / "text" / "PSI-107"
    folder.mkdir(parents=True)
    (folder / PSI_107_JSON.name).write_bytes(PSI_107_JSON.read_bytes())

    return tmp_path / "text"


def run(llm, tmp_path: Path, text_dir: Path, catalog=CATALOG, psi_ids=("PSI-107",)):
    return run_extraction(
        list(psi_ids),
        catalog,
        llm,
        model="test-model",
        text_dir=text_dir,
        insights_path=tmp_path / "out" / "insights.json",
        rejected_path=tmp_path / "out" / "rejected.json",
    )


def read(tmp_path: Path, name: str) -> dict:
    return json.loads((tmp_path / "out" / name).read_text(encoding="utf-8"))


def test_end_to_end_with_a_fake_model_writes_valid_official_json(
    tmp_path: Path, text_dir: Path
) -> None:
    run(FakeLlm(GOOD, INVENTED, NOTHING), tmp_path, text_dir)
    document = InsightsDocument.model_validate(read(tmp_path, "insights.json"))

    assert [i.title for i in document.insights] == ["Apparatus", "Nothing"]
    assert document.model == "test-model"
    assert document.prompt_version == PROMPT_VERSION
    assert document.generated_at.tzinfo is not None
    citation = document.insights[0].citations[0]
    assert (citation.psi_id, citation.doi, citation.page) == (
        "PSI-107",
        "10.1234/spice",
        10,
    )


def test_rejected_json_lists_what_failed_and_why(
    tmp_path: Path, text_dir: Path
) -> None:
    run(FakeLlm(GOOD, INVENTED), tmp_path, text_dir)
    rejected = read(tmp_path, "rejected.json")

    assert [r["title"] for r in rejected["rejected"]] == ["Invented"]
    assert rejected["rejected"][0]["psi_id"] == "PSI-107"
    assert "not found" in rejected["rejected"][0]["reasons"][0]
    assert rejected["model"] == "test-model"
    assert rejected["warnings"] == []


def test_the_model_receives_the_prompt_and_the_marked_pages(
    tmp_path: Path, text_dir: Path
) -> None:
    llm = FakeLlm(GOOD)
    run(llm, tmp_path, text_dir)
    system, user = llm.calls[0]

    assert "Do not write a DOI" in system
    assert "[PAGE 10]" in user and "PSI-107" in user
    assert len(llm.calls) == 1


def test_missing_doi_is_a_warning_in_rejected_json(
    tmp_path: Path, text_dir: Path
) -> None:
    run(FakeLlm(GOOD), tmp_path, text_dir, catalog={})

    assert read(tmp_path, "rejected.json")["warnings"] == [
        "No DOI in the catalog for PSI-107."
    ]
    assert read(tmp_path, "insights.json")["insights"][0]["citations"][0]["doi"] is None


def test_malformed_insight_is_rejected_but_the_others_survive(
    tmp_path: Path, text_dir: Path
) -> None:
    broken = {"title": "No status"}
    run(FakeLlm(GOOD, broken), tmp_path, text_dir)
    rejected = read(tmp_path, "rejected.json")["rejected"]

    assert len(read(tmp_path, "insights.json")["insights"]) == 1
    assert rejected[0]["title"] == "<malformed insight>"
    assert rejected[0]["reasons"][0].startswith("Insight #2:")


def test_when_nothing_survives_it_raises_and_writes_no_insights_json(
    tmp_path: Path, text_dir: Path
) -> None:
    insights_path = tmp_path / "out" / "insights.json"
    insights_path.parent.mkdir()
    insights_path.write_text('{"keep": "me"}', encoding="utf-8")

    with pytest.raises(RuntimeError, match="No insight survived"):
        run(FakeLlm(INVENTED), tmp_path, text_dir)

    assert insights_path.read_text(encoding="utf-8") == '{"keep": "me"}'
    assert len(read(tmp_path, "rejected.json")["rejected"]) == 1


def test_an_answer_that_is_not_json_raises_with_the_file_name(
    tmp_path: Path, text_dir: Path
) -> None:
    with pytest.raises(ValueError, match="PSI-107-SPICE-FinalReport.pdf"):
        run(FakeLlm(raw="I cannot help with that."), tmp_path, text_dir)

    assert not (tmp_path / "out" / "insights.json").exists()


def test_several_documents_are_combined_in_one_file(
    tmp_path: Path, text_dir: Path
) -> None:
    second = text_dir / "PSI-108"
    second.mkdir()
    doc = json.loads(PSI_107_JSON.read_text(encoding="utf-8"))
    doc.update(psi_id="PSI-108", filename="PSI-108-copy.pdf")
    (second / "PSI-108-copy.json").write_text(json.dumps(doc), encoding="utf-8")
    llm = FakeLlm(GOOD)
    run(llm, tmp_path, text_dir, catalog={"PSI-108": "10.9/b"}, psi_ids=("PSI-107", "PSI-108"))
    psi_ids = [
        i["citations"][0]["psi_id"] for i in read(tmp_path, "insights.json")["insights"]
    ]

    assert psi_ids == ["PSI-107", "PSI-108"]
    assert len(llm.calls) == 2


def test_extract_document_returns_the_assembled_result() -> None:
    doc = json.loads(PSI_107_JSON.read_text(encoding="utf-8"))
    result = extract_document(doc, CATALOG, FakeLlm(GOOD, INVENTED), 8)

    assert len(result.insights) == 1
    assert len(result.rejected) == 1


def test_find_text_files_fails_clearly_when_there_is_no_text(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="python -m src.pdf_text"):
        find_text_files("PSI-999", tmp_path)

    (tmp_path / "PSI-999").mkdir()

    with pytest.raises(FileNotFoundError, match="PSI-999"):
        find_text_files("PSI-999", tmp_path)
