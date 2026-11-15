import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.config import ESTIMATED_CHARS_PER_TOKEN
from src.llm import client
from src.llm.dry_run import format_preview, preview_request
from src.llm.prompts import SYSTEM_PROMPT, build_user_message
from src.paths import TEXT_DIR

PSI_107_JSON = TEXT_DIR / "PSI-107" / "PSI-107-SPICE-FinalReport.json"


@pytest.fixture(autouse=True)
def no_real_api(monkeypatch):
    """A dry run must never create the real SDK client or reach the network."""

    def forbidden(*args, **kwargs):
        raise AssertionError("A dry run tried to create the real API client.")

    monkeypatch.setattr(client.anthropic, "Anthropic", forbidden)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture(scope="module")
def psi107() -> dict:
    return json.loads(PSI_107_JSON.read_text(encoding="utf-8"))


def test_preview_describes_the_real_document(psi107, tmp_path: Path) -> None:
    preview = preview_request(psi107, "m", 100, tmp_path)

    assert preview.psi_id == "PSI-107"
    assert preview.filename == psi107["filename"]
    assert preview.pages_sent + preview.pages_skipped == len(psi107["pages"])
    assert preview.pages_sent == build_user_message(psi107).count("[PAGE ")
    assert preview.characters == len(SYSTEM_PROMPT) + len(
        build_user_message(psi107)
    )
    assert preview.estimated_input_tokens == math.ceil(
        preview.characters / ESTIMATED_CHARS_PER_TOKEN
    )
    assert preview.cached is False
    assert list(tmp_path.iterdir()) == []


def test_empty_pages_are_counted_as_skipped(tmp_path: Path) -> None:
    doc = {
        "psi_id": "PSI-000",
        "filename": "PSI-000-test.pdf",
        "pages": [
            {"page_number": 1, "text": "first page", "is_empty": False},
            {"page_number": 2, "text": "  \n", "is_empty": True},
        ],
    }
    preview = preview_request(doc, "m", 100, tmp_path)

    assert (preview.pages_sent, preview.pages_skipped) == (1, 1)


def test_preview_says_cache_hit_after_a_real_answer_was_stored(
    psi107, tmp_path: Path
) -> None:
    class Sdk:
        messages = SimpleNamespace(
            create=lambda **request: SimpleNamespace(
                content=[SimpleNamespace(type="text", text="stored")],
                stop_reason="end_turn",
                usage=SimpleNamespace(input_tokens=1, output_tokens=1),
            )
        )

    client.complete(
        SYSTEM_PROMPT,
        build_user_message(psi107),
        model="m",
        max_tokens=100,
        cache_dir=tmp_path,
        sdk_client=Sdk(),
    )

    assert preview_request(psi107, "m", 100, tmp_path).cached is True
    assert preview_request(psi107, "other", 100, tmp_path).cached is False


def test_a_malformed_document_raises_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="pages"):
        preview_request({"psi_id": "PSI-000"}, "m", 100, tmp_path)


def test_format_says_what_would_be_paid(psi107, tmp_path: Path) -> None:
    line = format_preview(preview_request(psi107, "m", 100, tmp_path))

    assert line.startswith("PSI-107 ")
    assert "input tokens (estimate)" in line
    assert "cache miss (would call the paid API)" in line
