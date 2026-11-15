import hashlib
import json
from pathlib import Path


def build_cache_key(request: dict) -> str:
    """Build a deterministic SHA-256 key from an API request."""

    serialized_request = json.dumps(
        request,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized_request.encode("utf-8")
    ).hexdigest()


def _get_cache_path(key: str, cache_dir: Path) -> Path:
    """Build the path for a cached response."""

    return cache_dir / f"{key}.json"


def get_cached_response(key: str, cache_dir: Path) -> dict | None:
    """Retrieve a cached response if it exists and is valid."""

    cache_path = _get_cache_path(key, cache_dir)

    if not cache_path.exists():
        return None

    try:
        with cache_path.open("r", encoding="utf-8") as file:
            entry = json.load(file)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        print(f"Corrupt cache file ignored: {cache_path}")
        return None

    if not isinstance(entry, dict):
        print(f"Invalid cache entry ignored: {cache_path}")
        return None

    return entry


def save_cached_response(
    key: str,
    cache_dir: Path,
    entry: dict,
) -> Path:
    """Save a response in the cache."""

    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = _get_cache_path(key, cache_dir)

    with cache_path.open("w", encoding="utf-8") as file:
        json.dump(
            entry,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return cache_path
