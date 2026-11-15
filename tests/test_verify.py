import json

import pytest

from src.llm.schemas import Citation
from src.llm.verify import normalize, verify_citation
from src.paths import TEXT_DIR

# The file name and the 28 pages are the F1 contract for this report.
PSI_107_JSON = TEXT_DIR / "PSI-107" / "PSI-107-SPICE-FinalReport.json"

# Real sentence from page 10 of PSI-107 (the PDF breaks it across lines).
GLOVEBOX_QUOTE = (
    "Inside the Glovebox, the core of the apparatus is the Experimental "
    "Assembly which consists of a flow duct and its accessories."
)

# Unicode characters by code point (see src/llm/verify.py).
LEFT_DQUOTE = chr(0x201C)
RIGHT_DQUOTE = chr(0x201D)
RIGHT_SQUOTE = chr(0x2019)
EN_DASH = chr(0x2013)
EM_DASH = chr(0x2014)
SOFT_HYPHEN = chr(0x00AD)
LIGATURE_FFI = chr(0xFB03)
LIGATURE_FI = chr(0xFB01)
SUBSCRIPT_TWO = chr(0x2082)


@pytest.fixture(scope="module")
def psi107() -> dict:
    return json.loads(PSI_107_JSON.read_text(encoding="utf-8"))


def cite(page: int, quote: str) -> Citation:
    return Citation(psi_id="PSI-107", page=page, quote=quote)


def doc_with_pages(*texts: str) -> dict:
    return {
        "psi_id": "PSI-000",
        "filename": "PSI-000-test.pdf",
        "pages": [
            {"page_number": number, "text": text, "is_empty": not text.strip()}
            for number, text in enumerate(texts, start=1)
        ],
    }


def passes(quote: str, *page_texts: str, page: int = 1) -> bool:
    return verify_citation(cite(page, quote), doc_with_pages(*page_texts)).ok


# --- The five cases required by the team lead, on the real PSI-107 text ---


def test_quote_with_different_spaces_and_line_breaks_passes(psi107) -> None:
    messy = GLOVEBOX_QUOTE.replace(" the core", "   the\ncore").replace(
        " duct", "\n duct"
    )

    assert verify_citation(cite(10, GLOVEBOX_QUOTE), psi107).ok
    assert verify_citation(cite(10, messy), psi107).ok


@pytest.mark.parametrize(
    ("page", "quote"),
    [
        (2, "smoke points in non-buoyant laminar jet diffusion flames"),
        (2, "smoke points in nonbuoyant laminar jet diffusion flames"),
        (7, "changed to a stand-alone investigation of smoke point"),
        (7, "changed to a standalone investigation of smoke point"),
    ],
)
def test_word_split_by_hyphen_at_line_end_passes_with_or_without_hyphen(
    psi107, page: int, quote: str
) -> None:
    # The PDF has "non-" / "buoyant" (page 2) and "stand-" / "alone"
    # (page 7) split across two lines.
    assert verify_citation(cite(page, quote), psi107).ok


def test_invented_quote_fails(psi107) -> None:
    result = verify_citation(
        cite(10, "The flame propagated at 99 cm/s in every single test."), psi107
    )

    assert not result.ok
    assert "not found" in result.reason


def test_real_quote_on_the_wrong_page_fails(psi107) -> None:
    result = verify_citation(cite(5, GLOVEBOX_QUOTE), psi107)

    assert not result.ok
    assert "page 5" in result.reason


def test_page_out_of_range_fails_with_clear_reason(psi107) -> None:
    result = verify_citation(cite(999, GLOVEBOX_QUOTE), psi107)

    assert not result.ok
    assert "does not exist" in result.reason
    assert "28 pages" in result.reason


# --- Guards against normalizing too much ---


def test_removing_a_space_between_words_fails(psi107) -> None:
    assert not verify_citation(cite(10, "consists of a flowduct and its"), psi107).ok


def test_different_case_fails(psi107) -> None:
    assert not verify_citation(cite(10, GLOVEBOX_QUOTE.lower()), psi107).ok


def test_whitespace_only_quote_fails_instead_of_matching_everything(
    psi107,
) -> None:
    result = verify_citation(cite(10, "   \n  "), psi107)

    assert not result.ok
    assert "empty" in result.reason


def test_quote_must_start_at_a_word_boundary(psi107) -> None:
    assert not verify_citation(
        cite(10, "ovebox, the core of the apparatus is the"), psi107
    ).ok


def test_quote_must_end_at_a_word_boundary(psi107) -> None:
    assert not verify_citation(
        cite(10, "Inside the Glovebox, the core of the appar"), psi107
    ).ok


def test_quote_with_ellipsis_fails(psi107) -> None:
    assert not verify_citation(
        cite(10, "Inside the Glovebox ... its accessories."), psi107
    ).ok


def test_hyphen_is_not_invented_or_dropped_mid_line() -> None:
    assert passes("a non-buoyant flame", "a non-buoyant flame")
    assert not passes("a nonbuoyant flame", "a non-buoyant flame")
    assert not passes("a non buoyant flame", "a non-buoyant flame")


def test_numeric_range_split_across_lines_is_never_joined_into_one_number() -> None:
    page = "values of 20-\n24 mm"

    assert passes("values of 20-24 mm", page)
    assert not passes("values of 2024 mm", page)


def test_dash_at_line_end_is_not_a_split_word() -> None:
    page = "the flame" + EM_DASH + "\nthe smoke"

    assert not passes("the flamethe smoke", page)


def test_quote_cannot_span_two_pages() -> None:
    assert not passes(
        "the flame went out and the smoke rose",
        "at that point the flame went out",
        "and the smoke rose slowly",
    )


# --- Guards against normalizing too little ---


def test_soft_hyphen_at_line_end_counts_as_a_split_word() -> None:
    page = "a non" + SOFT_HYPHEN + "\nbuoyant flame"

    assert passes("a non-buoyant flame", page)
    assert passes("a nonbuoyant flame", page)


def test_quote_copied_with_its_own_line_break_and_hyphen_passes(psi107) -> None:
    assert verify_citation(
        cite(2, "smoke points in non-\nbuoyant laminar jet"), psi107
    ).ok


def test_ligatures_are_expanded() -> None:
    page = "The e" + LIGATURE_FFI + "cient " + LIGATURE_FI + "re suppression"

    assert passes("The efficient fire suppression", page)


def test_curly_quotes_and_dash_variants_are_unified_in_both_directions() -> None:
    curly = (
        f"The {LEFT_DQUOTE}flame{RIGHT_DQUOTE} didn{RIGHT_SQUOTE}t "
        f"spread {EN_DASH} it stayed"
    )
    straight = "The \"flame\" didn't spread - it stayed"

    assert passes(straight, curly)
    assert passes(curly, straight)


def test_nfkc_also_equates_subscripts_with_plain_digits() -> None:
    # Documented side effect of NFKC: "CO2" and "CO" + subscript two match.
    assert passes("emits CO2 gas", "emits CO" + SUBSCRIPT_TWO + " gas")


# --- Malformed input ---


def test_page_without_text_fails() -> None:
    result = verify_citation(cite(1, "anything"), doc_with_pages("  \n"))

    assert not result.ok
    assert "no extractable text" in result.reason


def test_document_without_pages_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="pages"):
        verify_citation(cite(1, "anything"), {"filename": "PSI-1-x.pdf"})


def test_page_without_text_field_raises_clear_error() -> None:
    doc = {"filename": "PSI-1-x.pdf", "pages": [{"page_number": 1}]}

    with pytest.raises(ValueError, match="text"):
        verify_citation(cite(1, "anything"), doc)


# --- normalize ---


def test_normalize_collapses_whitespace_and_merges_hyphenated_lines() -> None:
    assert normalize("  a \n\n b\t c ") == "a b c"
    assert normalize("non-\nbuoyant") == "non-buoyant"
    assert normalize("non-\nbuoyant", join_hyphenated=True) == "nonbuoyant"
    assert normalize("20-\n24", join_hyphenated=True) == "20-24"
    assert normalize("a well-known fact") == "a well-known fact"
    assert normalize("a well-known fact", join_hyphenated=True) == "a well-known fact"
