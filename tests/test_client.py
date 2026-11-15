import json
from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest

from src.llm import client
from src.llm.cache import build_cache_key, get_cached_response


@pytest.fixture(autouse=True)
def no_real_api(monkeypatch):
    """No test may create the real SDK client or reach the network."""

    def forbidden(*args, **kwargs):
        raise AssertionError("A test tried to create the real API client.")

    monkeypatch.setattr(client.anthropic, "Anthropic", forbidden)


class FakeSdk:
    """Stands in for the Anthropic SDK client and records every call."""

    def __init__(self, text="answer", stop_reason="end_turn", error=None):
        self.calls: list[dict] = []
        self._text = text
        self._stop_reason = stop_reason
        self._error = error
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **request):
        self.calls.append(request)

        if self._error is not None:
            raise self._error

        blocks = [SimpleNamespace(type="text", text=self._text)]

        return SimpleNamespace(
            content=blocks,
            stop_reason=self._stop_reason,
            usage=SimpleNamespace(input_tokens=11, output_tokens=7),
        )


def run(sdk, cache_dir: Path, system="sys", user="user", **kwargs) -> str:
    return client.complete(
        system, user, cache_dir=cache_dir, sdk_client=sdk, **kwargs
    )


def test_miss_calls_the_api_once_and_a_second_call_is_a_cache_hit(
    tmp_path: Path,
) -> None:
    sdk = FakeSdk(text="the answer")

    assert run(sdk, tmp_path) == "the answer"
    assert run(sdk, tmp_path) == "the answer"
    assert len(sdk.calls) == 1


def test_cache_hit_needs_no_key_and_no_sdk_client(
    tmp_path: Path, monkeypatch
) -> None:
    run(FakeSdk(text="stored"), tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert client.complete("sys", "user", cache_dir=tmp_path) == "stored"


def test_request_sent_is_exactly_what_is_hashed(tmp_path: Path) -> None:
    sdk = FakeSdk()
    run(sdk, tmp_path, model="m", max_tokens=50)
    sent = sdk.calls[0]

    assert sent == {
        "model": "m",
        "max_tokens": 50,
        "system": "sys",
        "messages": [{"role": "user", "content": "user"}],
    }
    assert not {"temperature", "top_p", "top_k"} & sent.keys()
    assert get_cached_response(build_cache_key(sent), tmp_path) is not None


def test_is_cached_reads_the_cache_without_key_sdk_or_writing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert not client.is_cached("sys", "user", cache_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []

    run(FakeSdk(text="stored"), tmp_path, model="m")

    assert client.is_cached("sys", "user", model="m", cache_dir=tmp_path)
    assert not client.is_cached("sys", "other", model="m", cache_dir=tmp_path)
    assert not client.is_cached("sys", "user", model="other", cache_dir=tmp_path)
    assert not client.is_cached(
        "sys", "user", model="m", max_tokens=1, cache_dir=tmp_path
    )


def test_an_entry_without_text_is_not_a_cache_hit(tmp_path: Path) -> None:
    request = client.build_request("sys", "user", "m", 5)
    (tmp_path / (build_cache_key(request) + ".json")).write_text(
        json.dumps({"text": "  "}), encoding="utf-8"
    )

    assert not client.is_cached(
        "sys", "user", model="m", max_tokens=5, cache_dir=tmp_path
    )


def test_a_different_prompt_or_setting_is_a_different_cache_entry(
    tmp_path: Path,
) -> None:
    sdk = FakeSdk()
    run(sdk, tmp_path, user="one")
    run(sdk, tmp_path, user="two")
    run(sdk, tmp_path, user="one", max_tokens=10)

    assert len(sdk.calls) == 3


def test_cache_entry_stores_the_real_response_metadata(tmp_path: Path) -> None:
    sdk = FakeSdk(text="x")
    run(sdk, tmp_path, model="m")
    entry = get_cached_response(build_cache_key(sdk.calls[0]), tmp_path)

    assert entry["text"] == "x"
    assert entry["model"] == "m"
    assert entry["usage"] == {"input_tokens": 11, "output_tokens": 7}
    assert entry["created_at"].endswith("+00:00")


def test_miss_without_key_fails_clearly_and_never_invents_data(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        client.complete("sys", "user", cache_dir=tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_api_failure_becomes_a_clear_error_and_is_not_cached(
    tmp_path: Path,
) -> None:
    sdk = FakeSdk(error=anthropic.APIConnectionError(request=object()))

    with pytest.raises(RuntimeError, match="Anthropic API call failed"):
        run(sdk, tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_answer_cut_at_max_tokens_raises_and_is_not_cached(
    tmp_path: Path,
) -> None:
    sdk = FakeSdk(text="{ cut", stop_reason="max_tokens")

    with pytest.raises(RuntimeError, match="max_tokens"):
        run(sdk, tmp_path, max_tokens=5)

    assert list(tmp_path.iterdir()) == []


def test_response_without_text_raises_and_is_not_cached(
    tmp_path: Path,
) -> None:
    with pytest.raises(RuntimeError, match="no text"):
        run(FakeSdk(text="  "), tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_cache_entry_without_text_is_treated_as_a_miss(tmp_path: Path) -> None:
    sdk = FakeSdk(text="fresh")
    run(sdk, tmp_path)
    key = build_cache_key(sdk.calls[0])
    (tmp_path / f"{key}.json").write_text('{"created_at": "x"}', encoding="utf-8")

    assert run(sdk, tmp_path) == "fresh"
    assert len(sdk.calls) == 2


@pytest.mark.parametrize("stop_reason", ["refusal", "pause_turn", None])
def test_answer_that_did_not_end_normally_is_not_cached(
    tmp_path: Path, stop_reason
) -> None:
    sdk = FakeSdk(text="partial", stop_reason=stop_reason)

    with pytest.raises(RuntimeError, match="not usable"):
        run(sdk, tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_stop_sequence_counts_as_a_normal_end(tmp_path: Path) -> None:
    assert run(FakeSdk(text="ok", stop_reason="stop_sequence"), tmp_path) == "ok"


def test_response_with_only_non_text_blocks_raises_and_is_not_cached(
    tmp_path: Path,
) -> None:
    sdk = FakeSdk()
    sdk.messages = SimpleNamespace(
        create=lambda **request: SimpleNamespace(
            content=[SimpleNamespace(type="tool_use")],
            stop_reason="end_turn",
            usage=None,
        )
    )

    with pytest.raises(RuntimeError, match="no text"):
        run(sdk, tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_answer_rejected_by_validate_is_not_cached(tmp_path: Path) -> None:
    sdk = FakeSdk(text="not json")

    def validate(text: str) -> None:
        raise ValueError("bad answer")

    with pytest.raises(ValueError, match="bad answer"):
        run(sdk, tmp_path, validate=validate)

    assert list(tmp_path.iterdir()) == []
    assert run(sdk, tmp_path) == "not json"
    assert len(sdk.calls) == 2


def test_validate_runs_on_a_miss_and_a_good_answer_is_cached(
    tmp_path: Path,
) -> None:
    seen: list[str] = []
    sdk = FakeSdk(text="good")

    assert run(sdk, tmp_path, validate=seen.append) == "good"
    assert run(sdk, tmp_path, validate=seen.append) == "good"
    assert seen == ["good"]
    assert len(sdk.calls) == 1


@pytest.mark.parametrize("stored", ["", "   \n", None, 5])
def test_cached_entry_with_blank_or_invalid_text_is_a_miss(
    tmp_path: Path, stored
) -> None:
    sdk = FakeSdk(text="fresh")
    run(sdk, tmp_path)
    key = build_cache_key(sdk.calls[0])
    entry = {"text": stored}
    (tmp_path / f"{key}.json").write_text(
        json.dumps(entry), encoding="utf-8"
    )

    assert run(sdk, tmp_path) == "fresh"
    assert len(sdk.calls) == 2
