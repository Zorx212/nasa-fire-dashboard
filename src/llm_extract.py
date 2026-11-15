import argparse
import json
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from src.catalog import load_catalog
from src.config import LLM_MAX_TOKENS, LLM_MODEL, MIN_QUOTE_WORDS
from src.llm.assemble import AssembleResult, Rejection, assemble_insights
from src.llm.client import complete
from src.llm.dry_run import RequestPreview, format_preview, preview_request
from src.llm.parse import parse_model_output
from src.llm.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_message
from src.llm.schemas import Insight, InsightsDocument
from src.paths import (
    CACHE_DIR,
    CATALOG_PATH,
    INSIGHTS_PATH,
    REJECTED_PATH,
    TEXT_DIR,
)

MALFORMED_TITLE = "<malformed insight>"
UNUSABLE_TITLE = "<unusable model answer>"
TEXT_FILE_PATTERN = "*.json"
PDF_TEXT_COMMAND = "python -m src.pdf_text <path to the PDF>"

# A function that takes (system prompt, user message) and returns the
# model's text. The real one goes through the cache and the API.
LlmCall = Callable[[str, str], str]


def find_text_files(psi_id: str, text_dir: Path = TEXT_DIR) -> list[Path]:
    """Return the extracted-text JSON files of a PSI or raise clearly."""
    folder = Path(text_dir) / psi_id
    files = sorted(folder.glob(TEXT_FILE_PATTERN)) if folder.is_dir() else []

    if not files:
        raise FileNotFoundError(
            f"No extracted text for {psi_id} in {folder}. "
            f"Run: {PDF_TEXT_COMMAND}"
        )

    return files


def load_extracted_doc(text_path: Path) -> dict:
    """Read one extracted-text JSON file."""
    with Path(text_path).open("r", encoding="utf-8") as file:
        return json.load(file)


def check_answer(text: str) -> None:
    """Raise ValueError if the model's text is not usable (so it is not cached)."""
    parse_model_output(text)


def extract_document(
    extracted_doc: dict,
    catalog: dict[str, str],
    llm_call: LlmCall,
    min_quote_words: int = MIN_QUOTE_WORDS,
) -> AssembleResult:
    """Ask the model about one document and verify what it answers.

    Insights the model wrote with the wrong shape are added to the rejected
    list with their position and raw value. Raises ValueError, naming the
    file, if the answer is not a JSON object with an 'insights' list.
    """
    name = extracted_doc.get("filename", "<unknown file>")

    try:
        answer = llm_call(SYSTEM_PROMPT, build_user_message(extracted_doc))
        parsed = parse_model_output(answer)
    except ValueError as error:
        raise ValueError(f"{name}: {error}") from error

    result = assemble_insights(
        parsed.insights, extracted_doc, catalog, min_quote_words
    )
    psi_id = extracted_doc["psi_id"]
    malformed = [
        Rejection(
            psi_id=psi_id,
            title=MALFORMED_TITLE,
            reasons=[failure.message],
            insight=(
                failure.raw
                if isinstance(failure.raw, dict)
                else {"raw": failure.raw}
            ),
        )
        for failure in parsed.errors
    ]

    return AssembleResult(
        result.insights, result.rejected + malformed, result.warnings
    )


def _write_json(path: Path, data: dict) -> None:
    """Write data as JSON through a temporary file, so a crash cannot leave
    a half-written file in place of a good one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    temporary.replace(path)


def _check_requested_psi(extracted_doc: dict, psi_id: str, text_path: Path) -> None:
    """Raise ValueError if a file says it is another PSI than the requested one."""
    found = extracted_doc.get("psi_id")

    if found != psi_id:
        raise ValueError(
            f"{text_path} says psi_id={found!r} but {psi_id} was requested."
        )


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
    """Extract, verify and write insights.json and insights_rejected.json.

    A document whose answer is unusable does not stop the others: it is
    listed in insights_rejected.json, which is always written. insights.json
    is written only if at least one insight survived; otherwise
    RuntimeError is raised and an existing insights.json is left untouched.
    Errors that are not about one answer (no key, no internet, a file that
    names another PSI) stop the run.
    """
    insights: list[Insight] = []
    rejected: list[Rejection] = []
    warnings: list[str] = []

    for psi_id in psi_ids:
        for text_path in find_text_files(psi_id, text_dir):
            extracted_doc = load_extracted_doc(text_path)
            _check_requested_psi(extracted_doc, psi_id, text_path)

            try:
                result = extract_document(
                    extracted_doc, catalog, llm_call, min_quote_words
                )
            except ValueError as error:
                rejected.append(
                    Rejection(
                        psi_id=psi_id,
                        title=UNUSABLE_TITLE,
                        reasons=[str(error)],
                        insight={},
                    )
                )
                continue

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


def run_dry_run(
    psi_ids: list[str],
    model: str = LLM_MODEL,
    max_tokens: int = LLM_MAX_TOKENS,
    text_dir: Path = TEXT_DIR,
    cache_dir: Path = CACHE_DIR,
) -> list[RequestPreview]:
    """Describe every request a real run would make. Calls nothing, writes nothing.

    Needs no API key and no catalog. Raises the same errors as a real run
    for missing text or a file that names another PSI.
    """
    previews = []

    for psi_id in psi_ids:
        for text_path in find_text_files(psi_id, text_dir):
            extracted_doc = load_extracted_doc(text_path)
            _check_requested_psi(extracted_doc, psi_id, text_path)
            previews.append(
                preview_request(extracted_doc, model, max_tokens, cache_dir)
            )

    return previews


def _print_dry_run(previews: list[RequestPreview], model: str) -> None:
    """Print one line per request and a summary of what would be paid."""
    print(f"Dry run. Model {model}, prompt {PROMPT_VERSION}.")

    for preview in previews:
        print(format_preview(preview))

    misses = [preview for preview in previews if not preview.cached]
    tokens = sum(preview.estimated_input_tokens for preview in misses)
    print(
        f"{len(previews)} request(s); {len(misses)} would call the paid API "
        f"(about {tokens} input tokens in total, an estimate). "
        "Nothing was sent and nothing was written."
    )


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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show the requests (page blocks, estimated tokens, cache hit or "
            "miss) without calling the API or writing files."
        ),
    )
    args = parser.parse_args()
    model = LLM_MODEL

    if args.dry_run:
        try:
            previews = run_dry_run(args.psi_ids, model, cache_dir=CACHE_DIR)
            _print_dry_run(previews, model)
        except (ValueError, FileNotFoundError) as error:
            print(f"Error: {error}", file=sys.stderr)
            raise SystemExit(1) from error

        return

    try:
        catalog = _load_catalog(args.catalog, args.no_catalog)
        print(
            f"Model {model}, prompt {PROMPT_VERSION}. "
            "Cached answers are free; a cache miss calls the paid API."
        )
        document = run_extraction(
            args.psi_ids,
            catalog,
            lambda system, user: complete(
                system, user, model=model, validate=check_answer
            ),
            model=model,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(f"Wrote {len(document.insights)} insight(s) to {INSIGHTS_PATH}")
    print(
        "Rejected insights and warnings: "
        f"{REJECTED_PATH}. A run replaces insights.json, so list every "
        "PSI in one command."
    )


if __name__ == "__main__":
    main()
