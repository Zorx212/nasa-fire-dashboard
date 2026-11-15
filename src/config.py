import os
from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.environ.get("LLM_MODEL") or "claude-sonnet-5-5"

LLM_MAX_TOKENS = 4096
# Only for --dry-run: a rough size estimate, not the tokenizer's count.
ESTIMATED_CHARS_PER_TOKEN = 4
MIN_QUOTE_WORDS = 8
MAX_INSIGHTS_PER_DOC = 5


def get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Falta variable de entorno: ANTHROPIC_API_KEY")
    return key
