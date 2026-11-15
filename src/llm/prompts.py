from src.config import MAX_INSIGHTS_PER_DOC, MIN_QUOTE_WORDS

# Bump this when the prompt text changes: the cache key depends on the text,
# and insights.json records the version that produced it.
PROMPT_VERSION = "1.0.0"

_OUTPUT_EXAMPLE = """{
  "insights": [
    {
      "title": "short title",
      "description": "one or two sentences with the finding",
      "evidence_status": "supported",
      "confidence": "medium",
      "citations": [
        {"page": 10, "quote": "exact words copied from page 10"}
      ],
      "explanation": "why the quoted passages support the finding"
    },
    {
      "title": "short title",
      "description": "what the document does not establish",
      "evidence_status": "insufficient_data",
      "confidence": null,
      "citations": [],
      "explanation": "why the document is not enough"
    }
  ]
}"""

SYSTEM_PROMPT = (
    "You extract insights about fire safety and flame behavior in "
    "microgravity from one NASA PSI research document. You are given the "
    "text of the document page by page, each page marked [PAGE n].\n"
    "\n"
    "Rules:\n"
    "1. Use ONLY the text provided. Do not use outside knowledge.\n"
    f"2. Return at most {MAX_INSIGHTS_PER_DOC} insights, the most useful "
    "ones for comparing flame behavior (materials, oxygen, pressure, flow, "
    "gravity, outcomes).\n"
    "3. evidence_status is \"supported\" or \"insufficient_data\".\n"
    "   - supported: confidence is \"high\", \"medium\" or \"low\" and there "
    "is at least one citation.\n"
    "   - insufficient_data: confidence is null and citations is an empty "
    "list. Use it only to state that the document does not give enough "
    "information about a relevant topic.\n"
    "4. Every quote must be copied word for word from the text of ONE page: "
    f"at least {MIN_QUOTE_WORDS} words, no ellipsis, no paraphrase, no "
    "translation, no joining of separate sentences. Do not fix typos.\n"
    "5. page is the number in the [PAGE n] marker of the page that holds "
    "the quote (the position in the PDF, not a printed page number).\n"
    "6. Copy numbers and units exactly as written. Never invent values.\n"
    "7. Do not write a DOI or a document id: they are added later.\n"
    "8. Write title, description and explanation in Spanish (Mexico). "
    "Quotes stay in the original language.\n"
    "9. Answer with ONLY a JSON object in this shape, with no text before "
    "or after it:\n"
    f"{_OUTPUT_EXAMPLE}"
)


def build_user_message(extracted_doc: dict) -> str:
    """Build the user message: the document header and each page's raw text.

    Pages are marked "[PAGE n]" with n as the 1-based position in the PDF.
    Empty pages are skipped. The text is sent as extracted (not normalized).
    Raises ValueError if the document has no 'pages' list.
    """
    if not isinstance(extracted_doc, dict):
        raise ValueError("The extracted document must be a dict.")

    pages = extracted_doc.get("pages")

    if not isinstance(pages, list):
        raise ValueError("The extracted document has no 'pages' list.")

    parts = [
        f"Document: {extracted_doc.get('psi_id', '<unknown>')} "
        f"({extracted_doc.get('filename', '<unknown file>')})"
    ]

    for page in pages:
        if page.get("is_empty"):
            continue

        parts.append(f"[PAGE {page['page_number']}]\n{page['text']}")

    parts.append("Return the JSON object now.")

    return "\n\n".join(parts)
