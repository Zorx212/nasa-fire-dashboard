import os
from dotenv import load_dotenv

load_dotenv()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL")

if not ANTHROPIC_API_KEY:
    raise RuntimeError("Falta variable de entorno: ANTHROPIC_API_KEY")

if not LLM_MODEL:
    LLM_MODEL = "claude-sonnet-5-5"

