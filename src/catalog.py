import csv
import re
from pathlib import Path

REQUIRED_COLUMNS = ("psi_id", "doi")

# "https://doi.org/10.1/x", "http://dx.doi.org/10.1/x" or "doi:10.1/x".
_DOI_PREFIX = re.compile(
    r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE
)


def clean_doi(doi: str) -> str:
    """Return the bare DOI ("10.xxxx/...") without URL or "doi:" prefix."""
    return _DOI_PREFIX.sub("", doi.strip()).strip()


def _read_rows(catalog_path: Path) -> tuple[list[str], list[dict]]:
    """Return the stripped header and the rows of the CSV (UTF-8)."""
    try:
        with catalog_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            header = [name.strip() for name in reader.fieldnames or []]
            reader.fieldnames = header

            return header, list(reader)
    except UnicodeDecodeError as error:
        raise ValueError(
            f"Catalog {catalog_path.name} is not valid UTF-8. "
            "Save it again as 'CSV UTF-8'."
        ) from error


def load_catalog(catalog_path: Path) -> dict[str, str]:
    """Read the catalog CSV and return a {psi_id: doi} dict.

    Rows without a psi_id or without a DOI are skipped. Extra columns are
    ignored. Raises FileNotFoundError if the file is missing and ValueError
    if the file is not UTF-8, uses ';' as separator, lacks a required
    column or lists one psi_id with two different DOIs.
    """
    catalog_path = Path(catalog_path)

    if not catalog_path.is_file():
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")

    header, rows = _read_rows(catalog_path)

    if len(header) == 1 and ";" in header[0]:
        raise ValueError(
            f"Catalog {catalog_path.name} uses ';' as separator. "
            "Use commas."
        )

    missing = [column for column in REQUIRED_COLUMNS if column not in header]

    if missing:
        raise ValueError(
            f"Catalog {catalog_path.name} is missing required "
            f"column(s): {', '.join(missing)}."
        )

    catalog: dict[str, str] = {}

    for row in rows:
        psi_id = (row["psi_id"] or "").strip()
        doi = clean_doi(row["doi"] or "")

        if not psi_id or not doi:
            continue

        if psi_id in catalog and catalog[psi_id] != doi:
            raise ValueError(
                f"Catalog {catalog_path.name} lists two different "
                f"DOIs for {psi_id}."
            )

        catalog[psi_id] = doi

    return catalog


def get_doi(psi_id: str, catalog: dict[str, str]) -> str | None:
    """Return the DOI for a psi_id, or None if the catalog does not have it."""
    return catalog.get(psi_id.strip())
