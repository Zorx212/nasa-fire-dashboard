import argparse
import json
import re
from pathlib import Path

import pymupdf

from src.paths import TEXT_DIR


PSI_ID_PATTERN = re.compile(r"^(PSI-\d+)(?=$|[_\-. ])")


def extract_pdf_text(pdf_path: Path) -> dict:
    """Extract the text of a PDF page by page and return it as a dict."""
    pdf_path = Path(pdf_path)

    match = PSI_ID_PATTERN.match(pdf_path.name)

    if not match:
        raise ValueError(
            f"Invalid PDF filename: {pdf_path.name}. "
            "Expected a filename starting with PSI- followed by digits."
        )

    psi_id = match.group(1)
    pages = []

    with pymupdf.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text()

            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                    "is_empty": not text.strip(),
                }
            )

    return {
        "psi_id": psi_id,
        "filename": pdf_path.name,
        "pages": pages,
    }


def _get_output_path(document: dict) -> Path:
    """Single place that decides where a document's JSON is written."""
    filename = Path(document["filename"])

    return (
        TEXT_DIR
        / document["psi_id"]
        / f"{filename.stem}.json"
    )


def save_extracted_text(document: dict) -> Path:
    """Write the document as JSON (overwriting if it exists) and return its path."""
    output_path = _get_output_path(document)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        print(f"Overwriting existing file: {output_path}")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            document,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def main():
    """Command-line entry point: extract, save and print a short summary."""
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF, page by page."
    )

    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the PDF file.",
    )

    args = parser.parse_args()
    pdf_path = args.pdf_path

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    document = extract_pdf_text(pdf_path)
    output_path = save_extracted_text(document)

    empty_pages = sum(
        page["is_empty"] for page in document["pages"]
    )

    first_page_text = (
        document["pages"][0]["text"][:300]
        if document["pages"]
        else ""
    )

    print(f"PSI ID: {document['psi_id']}")
    print(f"Total pages: {len(document['pages'])}")
    print(f"Empty pages: {empty_pages}")
    print(f"First page preview (300 characters):\n{first_page_text}")
    print(f"Output file: {output_path}")


if __name__ == "__main__":
    main()