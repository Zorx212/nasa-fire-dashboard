import re
from pathlib import Path
import pandas as pd

RAW = Path("data/raw")


def psi_id_from_folder(name: str) -> str:
    m = re.match(r"psi[_-]?(\d+)", name, re.IGNORECASE)
    if not m:
        raise ValueError(f"La carpeta '{name}' debe empezar con PSI_<número>")
    return f"PSI-{int(m.group(1))}"


def read_csv_robust(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            df = pd.read_csv(path, sep=None, engine="python", encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"No pude leer {path}")
    df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True)
    df.columns = df.columns.str.replace(r"\s*-\s*", "-", regex=True)
    return df.dropna(how="all").reset_index(drop=True)


def ingest(raw_dir: Path = RAW) -> dict:
    """Devuelve {'PSI_159/archivo.csv': DataFrame} con la columna _psi_id añadida."""
    tables = {}
    for folder in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        psi_id = psi_id_from_folder(folder.name)
        for f in sorted(folder.rglob("*.csv")):
            df = read_csv_robust(f)
            df["_psi_id"] = psi_id
            tables[str(f.relative_to(raw_dir))] = df
    return tables


if __name__ == "__main__":
    for key, df in ingest().items():
        print(f"{key}: {len(df)} filas, {len(df.columns)} columnas")