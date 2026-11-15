import re
import unicodedata
from dataclasses import dataclass

from src.llm.schemas import Citation

# Unicode characters are written as code points on purpose: literal
# look-alike characters are unreadable and easy to alter by accident.
_CURLY_QUOTES = {
    0x2018: "'",  # left single quotation mark
    0x2019: "'",  # right single quotation mark
    0x201B: "'",  # single high-reversed-9 quotation mark
    0x201C: '"',  # left double quotation mark
    0x201D: '"',  # right double quotation mark
    0x201F: '"',  # double high-reversed-9 quotation mark
}
_HYPHEN_VARIANTS = {
    0x2010: "-",  # hyphen
    0x2011: "-",  # non-breaking hyphen
}
_LONG_DASHES = dict.fromkeys(
    (
        0x2012,  # figure dash
        0x2013,  # en dash
        0x2014,  # em dash
        0x2015,  # horizontal bar
        0x2212,  # minus sign
    ),
    "-",
)
_INVISIBLE = dict.fromkeys(
    (
        0x00AD,  # soft hyphen (the ones at a line end are handled before)
        0x200B,  # zero width space
        0x200C,  # zero width non-joiner
        0x200D,  # zero width joiner
        0x2060,  # word joiner
        0xFEFF,  # byte order mark
    ),
    None,
)

_BEFORE_JOIN = {**_CURLY_QUOTES, **_HYPHEN_VARIANTS, **_INVISIBLE}
_AFTER_JOIN = _LONG_DASHES

_SOFT_HYPHEN_AT_LINE_END = re.compile(
    re.escape(chr(0x00AD)) + r"(?=[ \t]*\r?\n)"
)
# Letter, hyphen, line break, letter: the PDF split one word in two lines.
_SPLIT_WORD = re.compile(r"(?<=[^\W\d_])-[ \t]*\r?\n[ \t]*(?=[^\W\d_])")
# Any word character on both sides (also digits, as in "20-\n24").
_HYPHEN_AT_LINE_END = re.compile(r"(?<=\w)-[ \t]*\r?\n[ \t]*(?=\w)")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of checking one citation: ok, or the reason it failed."""

    ok: bool
    reason: str | None = None


def normalize(text: str, join_hyphenated: bool = False) -> str:
    """Put text in a comparable form without changing its words.

    Applies NFKC (ligatures like the one in "fi" become plain letters, and
    "CO2" equals the subscript form, "cm2" equals "cm" squared), unifies
    curly quotes and dash variants, drops invisible characters and collapses
    all whitespace. A hyphen at the end of a line is merged with the next
    line: it is kept ("non-buoyant") or, if join_hyphenated is True, removed
    ("nonbuoyant"); only between two letters, so "20-\\n24" is always
    "20-24". Case and word spacing are not touched.
    """
    text = unicodedata.normalize("NFKC", text)
    text = _SOFT_HYPHEN_AT_LINE_END.sub("-", text)
    text = text.translate(_BEFORE_JOIN)

    if join_hyphenated:
        text = _SPLIT_WORD.sub("", text)

    text = _HYPHEN_AT_LINE_END.sub("-", text)
    text = text.translate(_AFTER_JOIN)

    return _WHITESPACE.sub(" ", text).strip()


def _get_pages(extracted_doc: dict) -> list[dict]:
    """Return the pages list of an extracted document or fail clearly."""
    pages = extracted_doc.get("pages")

    if not isinstance(pages, list):
        name = extracted_doc.get("filename", "<unknown file>")
        raise ValueError(f"Extracted document {name} has no 'pages' list.")

    return pages


def _find_page(pages: list[dict], page_number: int) -> dict | None:
    """Return the page dict with that 1-based number, or None."""
    for page in pages:
        if page.get("page_number") == page_number:
            return page

    return None


def _contains_whole_words(text: str, quote: str) -> bool:
    """True if quote is in text and does not start or end inside a word."""
    start = r"(?<!\w)" if quote[0].isalnum() else ""
    end = r"(?!\w)" if quote[-1].isalnum() else ""

    return re.search(start + re.escape(quote) + end, text) is not None


def verify_citation(
    citation: Citation, extracted_doc: dict
) -> VerificationResult:
    """Check that the citation's quote appears on its page of the document.

    The quote and the page text are normalized the same way; a word split
    by a hyphen at a line end is accepted with or without the hyphen, and
    the quote must start and end at word boundaries. Returns a failed result
    with a clear reason if the page does not exist, has no text, the quote
    is empty or the quote is not on that page. Raises ValueError if the
    document is malformed. It does not compare citation.psi_id with the
    document's psi_id and it does not require a minimum quote length: the
    coordinator and the prompt decide those.
    """
    pages = _get_pages(extracted_doc)
    page = _find_page(pages, citation.page)

    if page is None:
        return VerificationResult(
            False,
            f"Page {citation.page} does not exist "
            f"(the document has {len(pages)} pages).",
        )

    text = page.get("text")

    if not isinstance(text, str):
        name = extracted_doc.get("filename", "<unknown file>")
        raise ValueError(
            f"Page {citation.page} of {name} has no 'text' string."
        )

    if not text.strip():
        return VerificationResult(
            False, f"Page {citation.page} has no extractable text."
        )

    if not normalize(citation.quote):
        return VerificationResult(
            False, "The quote is empty after normalization."
        )

    for join_hyphenated in (False, True):
        quote = normalize(citation.quote, join_hyphenated)
        page_text = normalize(text, join_hyphenated)

        if _contains_whole_words(page_text, quote):
            return VerificationResult(True)

    return VerificationResult(
        False, f"The quote was not found on page {citation.page}."
    )
