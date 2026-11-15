from pathlib import Path

import pytest

from src.catalog import clean_doi, get_doi, load_catalog


def write_csv(path: Path, content: str, encoding: str = "utf-8") -> Path:
    path.write_text(content, encoding=encoding)
    return path


def test_finds_doi_for_known_psi_id(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "catalog.csv",
        "psi_id,doi,title\nPSI-107,10.1234/abc,SPICE\nPSI-108,10.1234/def,Other\n",
    )
    catalog = load_catalog(csv_path)

    assert get_doi("PSI-107", catalog) == "10.1234/abc"
    assert get_doi("PSI-108", catalog) == "10.1234/def"


def test_unknown_psi_id_returns_none(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "catalog.csv", "psi_id,doi\nPSI-107,10.1/a\n")

    assert get_doi("PSI-999", load_catalog(csv_path)) is None


def test_row_without_doi_counts_as_not_in_catalog(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "catalog.csv", "psi_id,doi\nPSI-107,\nPSI-108,10.1/b\n"
    )
    catalog = load_catalog(csv_path)

    assert get_doi("PSI-107", catalog) is None
    assert get_doi("PSI-108", catalog) == "10.1/b"


def test_extra_columns_and_column_order_do_not_matter(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "catalog.csv",
        "title,license,doi,psi_id\nSPICE,CC0-1.0,10.1/a,PSI-107\n",
    )

    assert get_doi("PSI-107", load_catalog(csv_path)) == "10.1/a"


def test_spaces_and_excel_bom_are_tolerated(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "catalog.csv",
        "psi_id , doi\n PSI-107 , 10.1/a \n",
        encoding="utf-8-sig",
    )
    catalog = load_catalog(csv_path)

    assert get_doi("PSI-107", catalog) == "10.1/a"
    assert get_doi(" PSI-107 ", catalog) == "10.1/a"


def test_missing_required_column_raises_clear_error(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "catalog.csv", "psi_id,title\nPSI-107,SPICE\n")

    with pytest.raises(ValueError, match="doi"):
        load_catalog(csv_path)


def test_missing_file_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="catalog.csv"):
        load_catalog(tmp_path / "catalog.csv")


def test_same_psi_id_with_two_different_dois_raises(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "catalog.csv",
        "psi_id,doi\nPSI-107,10.1/a\nPSI-107,10.1/other\n",
    )

    with pytest.raises(ValueError, match="PSI-107"):
        load_catalog(csv_path)


def test_repeated_identical_row_is_accepted(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "catalog.csv", "psi_id,doi\nPSI-107,10.1/a\nPSI-107,10.1/a\n"
    )

    assert get_doi("PSI-107", load_catalog(csv_path)) == "10.1/a"


def test_file_saved_as_cp1252_raises_clear_error(tmp_path: Path) -> None:
    csv_path = tmp_path / "catalog.csv"
    csv_path.write_bytes(b"psi_id,doi,title\nPSI-107,10.1/a,Caf" + bytes([0xE9]) + b"\n")

    with pytest.raises(ValueError, match="UTF-8"):
        load_catalog(csv_path)


def test_semicolon_separator_raises_clear_error(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "catalog.csv", "psi_id;doi\nPSI-107;10.1/a\n")

    with pytest.raises(ValueError, match="separator"):
        load_catalog(csv_path)


def test_empty_file_raises_missing_column_error(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "catalog.csv", "")

    with pytest.raises(ValueError, match="psi_id, doi"):
        load_catalog(csv_path)


def test_header_only_returns_empty_catalog(tmp_path: Path) -> None:
    csv_path = write_csv(tmp_path / "catalog.csv", "psi_id,doi\n")

    assert load_catalog(csv_path) == {}


def test_windows_line_endings_are_accepted(tmp_path: Path) -> None:
    csv_path = tmp_path / "catalog.csv"
    csv_path.write_bytes(b"psi_id,doi\r\nPSI-107,10.1/a\r\n")

    assert get_doi("PSI-107", load_catalog(csv_path)) == "10.1/a"


def test_directory_instead_of_file_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_catalog(tmp_path)


@pytest.mark.parametrize(
    "raw",
    [
        "10.1234/abc",
        "  10.1234/abc  ",
        "https://doi.org/10.1234/abc",
        "http://dx.doi.org/10.1234/abc",
        "HTTPS://DOI.ORG/10.1234/abc",
        "doi:10.1234/abc",
        "DOI: 10.1234/abc",
    ],
)
def test_clean_doi_returns_the_bare_identifier(raw: str) -> None:
    assert clean_doi(raw) == "10.1234/abc"


def test_clean_doi_keeps_a_doi_that_contains_doi_org_inside() -> None:
    assert clean_doi("10.1234/see-doi.org/x") == "10.1234/see-doi.org/x"


def test_catalog_returns_clean_dois_and_same_doi_in_two_forms_is_not_a_conflict(
    tmp_path: Path,
) -> None:
    csv_path = write_csv(
        tmp_path / "catalog.csv",
        "psi_id,doi\n"
        "PSI-107,https://doi.org/10.1234/abc\n"
        "PSI-107,10.1234/abc\n"
        "PSI-108,doi:10.1234/def\n",
    )
    catalog = load_catalog(csv_path)

    assert get_doi("PSI-107", catalog) == "10.1234/abc"
    assert get_doi("PSI-108", catalog) == "10.1234/def"


def test_url_with_no_identifier_counts_as_not_in_catalog(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path / "catalog.csv", "psi_id,doi\nPSI-107,https://doi.org/\n"
    )

    assert get_doi("PSI-107", load_catalog(csv_path)) is None
