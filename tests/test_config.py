import pytest

from src import config


def test_no_sampling_setting_is_defined() -> None:
    # The API rejects temperature, top_p and top_k, so none may be configured.
    assert not hasattr(config, "LLM_TEMPERATURE")


def test_generation_limits_are_positive_integers() -> None:
    for value in (
        config.LLM_MAX_TOKENS,
        config.MIN_QUOTE_WORDS,
        config.MAX_INSIGHTS_PER_DOC,
    ):
        assert isinstance(value, int)
        assert value > 0


def test_get_api_key_reads_the_environment(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-value")

    assert config.get_api_key() == "test-value"


def test_get_api_key_fails_clearly_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        config.get_api_key()
