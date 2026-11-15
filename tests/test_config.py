import pytest

from src import config


def test_temperature_is_a_float_so_cache_keys_stay_stable() -> None:
    assert isinstance(config.LLM_TEMPERATURE, float)
    assert config.LLM_TEMPERATURE == 0.0


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
