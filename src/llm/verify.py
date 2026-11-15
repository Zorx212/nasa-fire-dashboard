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
# Superscripts are NOT turned into plain digits: "10" + superscript three is
# a different magnitude than "103". They become "^3", the same on both sides.
_SUPERSCRIPTS = {
    0x00B9: "^1",
    0x00B2: "^2",
    0x00B3: "^3",
    0x2070: "^0",
    0x2074: "^4",
    0x2075: "^5",
    0x2076: "^6",
    0x2077: "^7",
    0x2078: "^8",
    0x2079: "^9",
    0x207A: "^+",
    0x207B: "^-",
}
# Zero width characters are dropped before the soft hyphen rule runs.
_ZERO_WIDTH = dict.fromkeys(
    (
        0x200B,  # zero width space
        0x200C,  # zero width non-joiner
        0x200D,  # zero width joiner
        0x2060,  # word joiner
        0xFEFF,  # byte order mark
    ),
    None,
)
_SOFT_HYPHEN = {0x00AD: None}
# Dashes that mean a range or a minus sign. The em dash and the horizontal
# bar are left alone: they are punctuation, not a hyphen.
_RANGE_DASHES = dict.fromkeys(
    (
        0x2012,  # figure dash
        0x2013,  # en dash
        0x2212,  # minus sign
    ),
    "-",
)

_BEFORE_JOIN = {**_CURLY_QUOTES, **_HYPHEN_VARIANTS, **_SOFT_HYPHEN}
_AFTER_JOIN = _RANGE_DASHES

_SOFT_HYPHEN_AT_LINE_END = re.compile(
    re.escape(chr(0x00AD)) + r"(?=[ \t]*\r?\n)"
)
# Letter, hyphen, line break, letter: the PDF split one word in two lines.
_SPLIT_WORD = re.compile(r"(?<=[^\W\d_])-\s+(?=[^\W\d_])")
# Any word character on both sides (also digits, as in "20-\n24"). The line
# break may already be a plain space, as when a model copies "non-\nbuoyant"
# as "non- buoyant".
_HYPHEN_AT_LINE_END = re.compile(r"(?<=\w)-\s+(?=\w)")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of checking one citation: ok, or the reason it failed."""

    ok: bool
    reason: str | None = None


def normalize(text: str, join_hyphenated: bool = False) -> str:
    """Put text in a comparable form without changing its words.

    Applies NFKC (ligatures like the one in "fi" become plain letters, and
    a subscript digit equals a plain digit, so "CO2" matches the subscript
    form), unifies curly quotes, hyphen and range-dash variants, drops
    invisible characters and collapses all whitespace. Superscripts are kept
    distinct from plain digits. A hyphen followed by a line break (or by a
    space, if the line break was already flattened) is merged with the next
    word: the hyphen is always kept between two word characters
    ("non-buoyant", "20-24"); if join_hyphenated is True it is removed
    ("nonbuoyant") only between two letters, so "20-\\n24" is always
    "20-24". Case and word spacing are not touched.
    """
    text = text.translate(_SUPERSCRIPTS)
    text = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH)
    text = _SOFT_HYPHEN_AT_LINE_END.sub("-", text)
    text = text.translate(_BEFORE_JOIN)

    if join_hyphenated:
        text = _SPLIT_WORD.sub("", text)

    text = _HYPHEN_AT_LINE_END.sub("-", text)
    text = text.translate(_AFTER_JOIN)

    return _WHITESPACE.sub(" ", text).strip()


def _get_pages(extracted_doc: dict) -> list[dict]:
    """Return the pages list of an extracted document or fail clearly."""
    if not isinstance(extracted_doc, dict):
        raise ValueError("The extracted document must be a dict.")

    pages = extracted_doc.get("pages")

    if not isinstance(pages, list):
        name = extracted_doc.get("filename", "<unknown file>")
        raise ValueError(f"Extracted document {name} has no 'pages' list.")

    return pages


def _find_page(pages: list[dict], page_number: int) -> dict | None:
    """Return the page dict with that 1-based number, or None."""
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Every item of 'pages' must be a dict.")

        if page.get("page_number") == page_number:
            return page

    return None


def _contains_whole_words(text: str, quote: str) -> bool:
    """True if quote is in text without cutting a word, number or compound.

    The quote must not start or end inside a word. It also must not start
    inside a number (the "6" of "1.6", the "5" of "-5", the "24" of "20-24")
    or after the first part of a compound ("buoyant" of "non-buoyant"), nor
    end before the rest of them ("20" of "20-24", "non" of "non-buoyant").
    """
    first, last = quote[0], quote[-1]
    start = r"(?<!\w)"
    end = r"(?!\w)"

    if first.isdigit():
        start += r"(?<![-+.,/])"
    elif first.isalpha():
        start += r"(?<!\w[-/])"

    if last.isalnum():
        end += r"(?![-/]\w)"

        if last.isdigit():
            end += r"(?![.,]\d)"
    elif last == "." and len(quote) > 1 and (quote[-2].isalpha() or quote[-2] == ")"):
        # A sentence end may be glued to a footnote marker ("air.5").
        end = ""

    return re.search(start + re.escape(quote) + end, text) is not None


def verify_citation(
    citation: Citation, extracted_doc: dict
) -> VerificationResult:
    """Check that the citation's quote appears on its page of the document.

    The quote and the page text are normalized the same way; a word split
    by a hyphen at a line end is accepted with or without the hyphen, and
    the quote must not cut a word, a number or a hyphenated compound at
    either end. Returns a failed result with a clear reason if the page does
    not exist, has no text, the quote is empty or the quote is not on that
    page. Raises ValueError if the document is malformed. It does not
    compare citation.psi_id with the document's psi_id and it does not
    require a minimum quote length: the coordinator and the prompt decide
    those.
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
