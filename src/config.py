import os
from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.environ.get("LLM_MODEL") or "claude-sonnet-5-5"

# Always a float: 0 and 0.0 produce different cache keys.
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 4096
MIN_QUOTE_WORDS = 8
MAX_INSIGHTS_PER_DOC = 5


def get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Falta variable de entorno: ANTHROPIC_API_KEY")
    return key
