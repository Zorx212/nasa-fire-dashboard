import json
from pathlib import Path

from src.llm.cache import (
    build_cache_key,
    get_cached_response,
    save_cached_response,
)

REQUEST = {
    "model": "test-model",
    "max_tokens": 100,
    "temperature": 0,
    "system": "Responde solo con datos del reporte.",
    "messages": [{"role": "user", "content": "¿Cuál es la presión?"}],
}


def test_key_is_stable_for_same_request_with_different_key_order() -> None:
    reordered = dict(reversed(list(REQUEST.items())))

    assert build_cache_key(REQUEST) == build_cache_key(reordered)


def test_key_is_a_sha256_hex_digest() -> None:
    key = build_cache_key(REQUEST)

    assert len(key) == 64
    assert set(key) <= set("0123456789abcdef")


def test_key_matches_known_value_so_cached_files_stay_valid() -> None:
    request = {
        "temperature": 0,
        "model": "m",
        "messages": [{"role": "user", "content": "presión"}],
    }

    # Serialized as {"messages":[{"content":"presión","role":"user"}],
    # "model":"m","temperature":0} (sorted keys, compact, no \u escapes).
    assert build_cache_key(request) == (
        "84070194e898b2f668a80a61c9ee8976755f3fc6d9b7757338e595e341dba067"
    )


def test_key_changes_when_request_changes_by_one_character() -> None:
    changed = {**REQUEST, "system": "Responde solo con datos del reporte!"}

    assert build_cache_key(REQUEST) != build_cache_key(changed)


def test_miss_returns_none(tmp_path: Path) -> None:
    assert get_cached_response("missing", tmp_path) is None


def test_round_trip_keeps_accents(tmp_path: Path) -> None:
    entry = {"texto": "presión de oxígeno", "page": 3}

    save_cached_response("abc", tmp_path, entry)

    assert get_cached_response("abc", tmp_path) == entry
    assert "presión" in (tmp_path / "abc.json").read_text(encoding="utf-8")


def test_save_creates_missing_directory(tmp_path: Path) -> None:
    cache_dir = tmp_path / "nested" / "llm"

    path = save_cached_response("abc", cache_dir, {"ok": True})

    assert path == cache_dir / "abc.json"
    assert path.exists()


def test_corrupt_file_is_a_miss_with_warning(tmp_path: Path, capsys) -> None:
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")

    assert get_cached_response("bad", tmp_path) is None
    assert "Corrupt cache file ignored" in capsys.readouterr().out


def test_unreadable_cache_path_is_a_miss_with_warning(
    tmp_path: Path, capsys
) -> None:
    (tmp_path / "dir.json").mkdir()

    assert get_cached_response("dir", tmp_path) is None
    assert "Corrupt cache file ignored" in capsys.readouterr().out


def test_non_utf8_bytes_are_a_miss_with_warning(
    tmp_path: Path, capsys
) -> None:
    (tmp_path / "bytes.json").write_bytes(b"\xff\xfe\x00")

    assert get_cached_response("bytes", tmp_path) is None
    assert "Corrupt cache file ignored" in capsys.readouterr().out


def test_empty_file_is_a_miss_with_warning(tmp_path: Path, capsys) -> None:
    (tmp_path / "empty.json").write_bytes(b"")

    assert get_cached_response("empty", tmp_path) is None
    assert "Corrupt cache file ignored" in capsys.readouterr().out


def test_saving_again_overwrites_the_entry(tmp_path: Path) -> None:
    save_cached_response("abc", tmp_path, {"v": 1})
    save_cached_response("abc", tmp_path, {"v": 2, "nested": {"a": [1, 2]}})

    assert get_cached_response("abc", tmp_path) == {
        "v": 2,
        "nested": {"a": [1, 2]},
    }


def test_non_dict_json_is_a_miss_with_warning(tmp_path: Path, capsys) -> None:
    (tmp_path / "list.json").write_text(json.dumps([1, 2]), encoding="utf-8")

    assert get_cached_response("list", tmp_path) is None
    assert "Invalid cache entry ignored" in capsys.readouterr().out
