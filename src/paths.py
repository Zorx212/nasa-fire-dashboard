from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw"
TEXT_DIR = PROJECT_ROOT / "data" / "text"
CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "llm"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog.csv"
INSIGHTS_PATH = PROCESSED_DIR / "insights.json"
REJECTED_PATH = PROCESSED_DIR / "rejected.json"

