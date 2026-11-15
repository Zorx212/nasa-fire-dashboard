import argparse
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from src.catalog import load_catalog
from src.config import LLM_MODEL, MIN_QUOTE_WORDS
from src.llm.assemble import AssembleResult, Rejection, assemble_insights
from src.llm.client import complete
from src.llm.parse import parse_model_output
from src.llm.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_message
from src.llm.schemas import InsightsDocument
from src.paths import CATALOG_PATH, INSIGHTS_PATH, REJECTED_PATH, TEXT_DIR

# A function that takes (system prompt, user message) and returns the
# model's text. The real one goes through the cache and the API.
LlmCall = Callable[[str, str], str]


def find_text_files(psi_id: str, text_dir: Path = TEXT_DIR) -> list[Path]:
    """Return the extracted-text JSON files of a PSI or raise clearly."""
    folder = Path(text_dir) / psi_id
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []

    if not files:
        raise FileNotFoundError(
            f"No extracted text for {psi_id} in {folder}. "
            "Run: python -m src.pdf_text <path to the PDF>"
        )

    return files


def load_extracted_doc(text_path: Path) -> dict:
    """Read one extracted-text JSON file."""
    with Path(text_path).open("r", encoding="utf-8") as file:
        return json.load(file)


def extract_document(
    extracted_doc: dict,
    catalog: dict[str, str],
    llm_call: LlmCall,
    min_quote_words: int = MIN_QUOTE_WORDS,
) -> AssembleResult:
    """Ask the model about one document and verify what it answers.

    Insights the model wrote with the wrong shape are added to the rejected
    list with their position. Raises ValueError if the answer is not a JSON
    object with an 'insights' list.
    """
    name = extracted_doc.get("filename", "<unknown file>")
    answer = llm_call(SYSTEM_PROMPT, build_user_message(extracted_doc))

    try:
        parsed = parse_model_output(answer)
    except ValueError as error:
        raise ValueError(f"{name}: {error}") from error

    result = assemble_insights(
        parsed.insights, extracted_doc, catalog, min_quote_words
    )
    psi_id = extracted_doc["psi_id"]
    malformed = [
        Rejection(psi_id=psi_id, title="<malformed insight>", reasons=[error], insight={})
        for error in parsed.errors
    ]

    return AssembleResult(
        result.insights, result.rejected + malformed, result.warnings
    )


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def run_extraction(
    psi_ids: list[str],
    catalog: dict[str, str],
    llm_call: LlmCall,
    model: str = LLM_MODEL,
    text_dir: Path = TEXT_DIR,
    insights_path: Path = INSIGHTS_PATH,
    rejected_path: Path = REJECTED_PATH,
    min_quote_words: int = MIN_QUOTE_WORDS,
) -> InsightsDocument:
    """Extract, verify and write insights.json and rejected.json.

    rejected.json is always written. insights.json is written only if at
    least one insight survived; otherwise RuntimeError is raised and an
    existing insights.json is left untouched.
    """
    insights, rejected, warnings = [], [], []

    for psi_id in psi_ids:
        for text_path in find_text_files(psi_id, text_dir):
            result = extract_document(
                load_extracted_doc(text_path),
                catalog,
                llm_call,
                min_quote_words,
            )
            insights += result.insights
            rejected += result.rejected
            warnings += result.warnings

    generated_at = datetime.now(timezone.utc)
    _write_json(
        rejected_path,
        {
            "generated_at": generated_at.isoformat(),
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "rejected": [
                {
                    "psi_id": item.psi_id,
                    "title": item.title,
                    "reasons": item.reasons,
                    "insight": item.insight,
                }
                for item in rejected
            ],
            "warnings": warnings,
        },
    )

    if not insights:
        raise RuntimeError(
            "No insight survived verification, so insights.json was not "
            f"written. See {rejected_path}."
        )

    document = InsightsDocument(
        generated_at=generated_at,
        model=model,
        prompt_version=PROMPT_VERSION,
        insights=insights,
    )
    _write_json(insights_path, document.model_dump(mode="json"))

    return document


def _load_catalog(catalog_path: Path, allow_missing: bool) -> dict[str, str]:
    """Load the catalog; with allow_missing, a missing file means empty."""
    if allow_missing and not Path(catalog_path).is_file():
        return {}

    return load_catalog(catalog_path)


def main() -> None:
    """Command-line entry point: extract insights for one or more PSI."""
    parser = argparse.ArgumentParser(
        description="Extract verified insights from the text of PSI documents."
    )
    parser.add_argument("psi_ids", nargs="+", help="For example: PSI-107")
    parser.add_argument(
        "--catalog", type=Path, default=CATALOG_PATH, help="Path to catalog.csv."
    )
    parser.add_argument(
        "--no-catalog",
        action="store_true",
        help="Do not fail if the catalog is missing: citations get no DOI.",
    )
    args = parser.parse_args()

    catalog = _load_catalog(args.catalog, args.no_catalog)
    print(
        f"Model {LLM_MODEL}, prompt {PROMPT_VERSION}. "
        "Cached answers are free; a cache miss calls the paid API."
    )
    document = run_extraction(
        args.psi_ids,
        catalog,
        lambda system, user: complete(system, user, model=LLM_MODEL),
    )
    print(f"Wrote {len(document.insights)} insight(s) to {INSIGHTS_PATH}")
    print(f"Rejected insights and warnings: {REJECTED_PATH}")


if __name__ == "__main__":
    main()
