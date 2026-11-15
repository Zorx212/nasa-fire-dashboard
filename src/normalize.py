import re
from pathlib import Path
import pandas as pd
from src.ingest import ingest

# CONTRATO con Python 2 y Dev A: mismas columnas y orden que data/mock/master_table_mock.csv
MASTER_COLUMNS = [
    "experiment_id", "psi_id", "doi", "license", "title",
    "material_or_fuel", "material_type",
    "o2_percent", "pressure_kpa", "flow_velocity", "gravity_level",
    "flame_outcome", "flame_spread_rate", "spread_rate_unit",
    "source_file", "source_page", "notes",
]

# CONFIRMAR EN EL REPORTE DE PSI-159: SE y FT
OUTCOME_MAP = {"se": "self_extinguished", "ft": "flow_terminated", "-": None}

PRESSURE_TO_KPA = {"atm": 101.325, "kpa": 1.0, "pa": 0.001, "bar": 100.0,
                   "mbar": 0.1, "torr": 0.133322, "psi": 6.894757}

# Llave = ruta dentro de data/raw. Opciones por tabla:
#  id_columns        columnas que forman el ID del ensayo
#  text              destino: columna origen (se limpia a minúsculas)
#  text_strip_regex  destino: regex que se borra del texto
#  numeric           destino: (columna, factor)  -> valor * factor
#  pressure_text     destino: columna con texto tipo "1 atm" -> kPa
#  mapped            destino: (columna, {valor: categoría})
#  mapped_contains   destino: (columna, {subcadena: categoría})
#  constants         destino: valor fijo
#  notes_from        columnas que se copian a notes
SPECS = {
    "PSI_159/PSI-159_tabla_Inverse_Flames.csv": {
        "id_columns": ["Test"],
        "text": {"material_or_fuel": "Fuel"},
        "numeric": {"o2_percent": ("XO2", 100),                 # fracción -> %
                    "pressure_kpa": ("approx p (bar)", 100)},   # bar -> kPa
        "mapped": {"flame_outcome": ("Self-ext or flow term", OUTCOME_MAP)},
        "constants": {"material_type": "gas", "gravity_level": "microgravity"},
        "notes_from": ["Flame Type", "Hot ignition", "TFP", "Color",
                       "HC burnrate (mg/s)", "Comments"],
    },
    "PSI_159/PSI-159_tabla_Normal_Flames.csv": {
        "id_columns": ["Test"],
        "text": {"material_or_fuel": "Fuel"},
        "numeric": {"o2_percent": ("XO2 before test", 100),
                    "pressure_kpa": ("approx p (bar)", 100)},
        "mapped": {"flame_outcome": ("Self-ext or flow term", OUTCOME_MAP)},
        "constants": {"material_type": "gas", "gravity_level": "microgravity"},
        "notes_from": ["Flame Type", "Cool flame?", "XO2 after test",
                       "Hot ignition", "Comments"],
    },
    "PSI_101/PSI-101_tabla.csv": {
        "id_columns": ["SAME Test #", "Sample Type"],
        "text": {"material_or_fuel": "Sample Type"},
        "numeric": {"flow_velocity": ("Inlet velocity (cm/s)", 1)},   # cm/s
        "constants": {"material_type": "solid", "gravity_level": "microgravity"},
        "notes_from": ["Description", "Date", "Rt/R0", "Duration (sec)",
                       "Primary aging time (sec)", "Primary mixing time (sec)",
                       "Net aging time (sec)"],
    },
    "PSI_102/PSI-102_tabla.csv": {
        "id_columns": ["Sample #"],
        "text": {"material_or_fuel": "Sample Material"},
        "text_strip_regex": {"material_or_fuel": r":.*$"},
        "numeric": {"flow_velocity": ("Air Flow (cm/s)", 1)},         # cm/s
        "mapped_contains": {"material_type": ("Sample Material", {
            "teflon": "solid", "kapton": "solid",
            "silicone": "solid", "lampwick": "solid"})},
        "constants": {"gravity_level": "microgravity"},
        "notes_from": ["Sample Material", "Weight loss rate (mg/min)",
                       "Aging Duration (minutes)"],
    },
    "PSI_107/PSI-107_tabla.csv": {
        "id_columns": ["GMT date", "GMT ignition"],
        "text": {"material_or_fuel": "Fuel"},
        "numeric": {"flow_velocity": ("Air Rate (cm/s)", 1)},         # cm/s
        "constants": {"material_type": "gas", "gravity_level": "microgravity"},
        "notes_from": ["Nozzle (mm)", "Fuel Rate (sccm)", "Fuel Rate (mg/s)",
                       "HC Fuel Rate (mg/s)", "GMT Flame Off"],
    },
    "PSI_39/PSI-39_tabla.csv": {
        "id_columns": ["Flex Number"],
        "drop_exact_duplicates": True,
        "text": {"material_or_fuel": "Fuel"},
        "numeric": {"o2_percent": ("Oxygen", 100)},                   # fracción -> %
        "pressure_text": {"pressure_kpa": "Pressure"},                # "1 atm" -> kPa
        "constants": {"material_type": "liquid", "gravity_level": "microgravity"},
        "notes_from": ["Test Date", "CIR", "Fiber", "Nitrogen", "Helium"],  # N2 y He, fracción
    },
    # PSI_22: pendiente, falta revisar su estructura.
    # Si un PSI mide velocidad de propagación, agrega:
    #   "spread_rate": {"column": "...", "factor": 1, "unit": "mm/s"},
}


def clean_text(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip().str.lower()
    return s.str.replace(r"\s+", " ", regex=True).str.replace(r"\s+%", "%", regex=True)


def parse_pressure_kpa(value):
    m = re.match(r"\s*([\d.]+)\s*([a-zA-Z]+)", str(value))
    if not m:
        return float("nan")
    factor = PRESSURE_TO_KPA.get(m.group(2).lower())
    return float(m.group(1)) * factor if factor else float("nan")


def warn_lost(key, col, src, result):
    lost = int(result.isna().sum() - src.isna().sum())
    if lost > 0:
        print(f"[aviso] {key}: {lost} valores de '{col}' no se pudieron convertir")


def normalize_table(key: str, df: pd.DataFrame, spec: dict) -> pd.DataFrame:
    id_cols = spec["id_columns"]
    if spec.get("drop_exact_duplicates"):
        before = len(df)
        df = df.drop_duplicates()
        if len(df) < before:
            print(f"[aviso] {key}: se eliminaron {before - len(df)} filas idénticas")
    df = df[df[id_cols[0]].notna()].copy()
    out = pd.DataFrame(index=df.index)

    id_parts = df[id_cols].astype("string").apply(
        lambda r: "-".join(re.sub(r"[\s:]", "", x) for x in r.dropna()), axis=1)
    out["experiment_id"] = df["_psi_id"] + "-" + id_parts
    out["psi_id"] = df["_psi_id"]

    for target, col in spec.get("text", {}).items():
        out[target] = clean_text(df[col])
    for target, pattern in spec.get("text_strip_regex", {}).items():
        out[target] = out[target].str.replace(pattern, "", regex=True).str.strip()

    for target, (col, factor) in spec.get("numeric", {}).items():
        out[target] = pd.to_numeric(df[col], errors="coerce") * factor
        warn_lost(key, col, df[col], out[target])

    for target, col in spec.get("pressure_text", {}).items():
        out[target] = df[col].map(parse_pressure_kpa)
        warn_lost(key, col, df[col], out[target])

    for target, (col, mapping) in spec.get("mapped", {}).items():
        raw = df[col].astype("string").str.strip().str.lower()
        out[target] = raw.map(mapping).astype("string")
        unknown = sorted(set(raw.dropna()) - set(mapping))
        if unknown:
            print(f"[aviso] {key}: valores sin mapear en '{col}': {unknown}")

    for target, (col, mapping) in spec.get("mapped_contains", {}).items():
        out[target] = df[col].map(
            lambda v: next((val for k, val in mapping.items() if k in str(v).lower()), pd.NA)
        ).astype("string")
        missing = df.loc[out[target].isna(), col].unique()
        if len(missing):
            print(f"[aviso] {key}: '{target}' vacío para: {list(missing)}")

    for target, value in spec.get("constants", {}).items():
        out[target] = value

    if "spread_rate" in spec:
        s = spec["spread_rate"]
        out["flame_spread_rate"] = pd.to_numeric(df[s["column"]], errors="coerce") * s.get("factor", 1)
        out["spread_rate_unit"] = s["unit"]

    cols = [c for c in spec.get("notes_from", []) if c in df.columns]

    def build_note(row):
        parts = [f"{c}={str(row[c]).strip()}" for c in cols
                 if pd.notna(row[c]) and str(row[c]).strip() not in ("", "-")]
        return "; ".join(parts) or pd.NA

    out["notes"] = df.apply(build_note, axis=1)
    out["source_file"] = key
    return out


def load_catalog(path="data/catalog.csv") -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        print("[aviso] no existe data/catalog.csv: doi, license y title quedan vacíos. "
              "Haz git pull origin main.")
        return pd.DataFrame(columns=["psi_id", "title", "doi", "license"])
    cat = pd.read_csv(p)
    cat["psi_id"] = "PSI-" + cat["psi_id"].astype(str).str.extract(r"(\d+)")[0]
    return cat[["psi_id", "title", "doi", "license"]]


def make_ids_unique(master: pd.DataFrame) -> pd.DataFrame:
    dup = master["experiment_id"].duplicated(keep=False)
    if dup.any():
        print(f"[aviso] {int(dup.sum())} filas comparten experiment_id; agrego sufijo _2, _3...")
        n = master.groupby("experiment_id").cumcount()
        suffix = n.map(lambda i: "" if i == 0 else f"_{i + 1}")
        master["experiment_id"] = master["experiment_id"] + suffix
    return master


def build_master() -> pd.DataFrame:
    # Ignora diferencias entre espacios y guiones bajos en los nombres de archivo
    specs = {k.replace(" ", "_"): v for k, v in SPECS.items()}
    parts = []
    for key, df in ingest().items():
        spec = specs.get(key.replace(" ", "_"))
        if spec is None:
            print(f"[aviso] sin spec, se omite: {key}")
            continue
        parts.append(normalize_table(key, df, spec))
    if not parts:
        raise SystemExit("[ERROR] ningún CSV coincide con SPECS. Revisa las llaves.")
    master = pd.concat(parts, ignore_index=True)
    master = make_ids_unique(master)
    master = master.merge(load_catalog(), on="psi_id", how="left")
    return master.reindex(columns=MASTER_COLUMNS)  # lo que falta queda vacío, nunca 0


CONTRACT_COLUMNS = [
    "experiment_id", "psi_id", "doi", "license", "title", "material_or_fuel",
    "material_type", "o2_percent", "pressure_kpa", "flow_velocity", "gravity_level",
    "flame_outcome", "flame_spread_rate", "spread_rate_unit", "source_file",
    "source_page", "notes",
]


def check_contract(master: pd.DataFrame, mock_path="data/mock/master_table_mock.csv"):
    p = Path(mock_path)
    expected = list(pd.read_csv(p, nrows=0).columns) if p.exists() else CONTRACT_COLUMNS
    origin = "el mock" if p.exists() else "la lista del contrato (no hay mock)"
    if list(master.columns) == expected:
        print(f"[ok] columnas idénticas a {origin}, mismo orden")
    else:
        print(f"[ERROR] las columnas NO coinciden con {origin}:")
        print("  esperadas:", expected)
        print("  mías     :", list(master.columns))

if __name__ == "__main__":
    m = build_master()
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    m.to_csv("data/processed/master_table.csv", index=False)
    print("filas x columnas:", m.shape)
    print(m.groupby("psi_id").size().to_string())
    print("experiment_id duplicados:", m["experiment_id"].duplicated().sum())
    check_contract(m)
    print(m.isna().mean().round(2).to_string())