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

# SE = self-extinguished ("se extinguió").
# FT (flow terminated) se deja vacío: describe cómo terminó la prueba, no el
# resultado de la llama. Ver notes/discoveries.md. El código original queda en notes.
OUTCOME_MAP = {"se": "se extinguió", "ft": None, "-": None}

# En PSI-99 (microgravedad), ?-g Burn Length == "~ 0" indica autoextinción inmediata;
# el resto de comportamientos (consumo total o llama anclada) quedan en notes.
PSI_99_OUTCOME_MAP = {
    "~ 0": "se extinguió",
    "29 cm": None,
    "5 cm & 0 (note 2)": None,
    "~ 10 cm (note 3)": None,
    "~ 10 cm (note 4)": None,
}

PRESSURE_TO_KPA = {"atm": 101.325, "kpa": 1.0, "pa": 0.001, "bar": 100.0,
                   "mbar": 0.1, "torr": 0.133322, "psi": 6.894757}

# Llave = ruta dentro de data/raw. Opciones por tabla:
#  id_columns             columnas que forman el ID del ensayo
#  id_regex               regex opcional para filtrar filas válidas por id_columns[0]
#  ffill_columns          columnas con celdas combinadas a rellenar hacia abajo
#  drop_exact_duplicates  elimina filas idénticas
#  text                   destino: columna origen (se limpia a minúsculas)
#  text_strip_regex       destino: regex que se borra del texto
#  numeric                destino: (columna, factor)  -> valor * factor
#  numeric_extract        destino: (columna, factor)  -> extrae número inicial antes de multiplicar
#  blank_negative         lista de destinos numéricos cuyos negativos pasan a vacío
#  flag_negative          destino: mensaje que se agrega a notes en las filas con valor negativo
#  pressure_text          destino: columna con texto tipo "1 atm" -> kPa
#  mapped                 destino: (columna, {valor: categoría})
#  mapped_contains        destino: (columna, {subcadena: categoría})
#  constants              destino: valor fijo
#  notes_from             columnas que se copian a notes
#  notes_const            textos fijos que se agregan a notes de todas las filas de la tabla
# gravity_level = 0 (en g): todos los experimentos son en microgravedad.
SPECS = {
    "PSI_159/PSI-159_tabla_Inverse_Flames.csv": {
        "id_columns": ["Test"],
        "text": {"material_or_fuel": "Fuel"},
        "numeric": {"o2_percent": ("XO2", 100),                 # fracción -> %
                    "pressure_kpa": ("approx p (bar)", 100)},   # bar -> kPa
        "mapped": {"flame_outcome": ("Self-ext or flow term", OUTCOME_MAP)},
        "constants": {"material_type": "gas", "gravity_level": 0},
        "notes_from": ["Flame Type", "Hot ignition", "TFP", "Color",
                       "HC burnrate (mg/s)", "Self-ext or flow term", "Comments"],
    },
    "PSI_159/PSI-159_tabla_Normal_Flames.csv": {
        "id_columns": ["Test"],
        "text": {"material_or_fuel": "Fuel"},
        "numeric": {"o2_percent": ("XO2 before test", 100),
                    "pressure_kpa": ("approx p (bar)", 100)},
        "mapped": {"flame_outcome": ("Self-ext or flow term", OUTCOME_MAP)},
        "constants": {"material_type": "gas", "gravity_level": 0},
        "notes_from": ["Flame Type", "Cool flame?", "XO2 after test",
                       "Hot ignition", "Self-ext or flow term", "Comments"],
    },
    "PSI_101/PSI-101_tabla.csv": {
        "id_columns": ["SAME Test #", "Sample Type"],
        "text": {"material_or_fuel": "Sample Type"},
        "numeric": {"flow_velocity": ("Inlet velocity (cm/s)", 1)},   # cm/s
        "constants": {"material_type": "sólido", "gravity_level": 0},
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
            "teflon": "sólido", "kapton": "sólido",
            "silicone": "sólido", "lampwick": "sólido",
            "dibutyl": "líquido"})},
        "constants": {"gravity_level": 0},
        "notes_from": ["Sample Material", "Weight loss rate (mg/min)",
                       "Aging Duration (minutes)"],
    },
    "PSI_107/PSI-107_tabla.csv": {
        "id_columns": ["GMT date", "GMT ignition"],
        "text": {"material_or_fuel": "Fuel"},
        "numeric": {"flow_velocity": ("Air Rate (cm/s)", 1)},         # cm/s
        # Negativos: se conservan y se marcan en notes hasta confirmar en el reporte.
        # Si el reporte dice que son error, usar "blank_negative": ["flow_velocity"]
        # y agregar "Air Rate (cm/s)" a notes_from para conservar el valor original.
        "flag_negative": {"flow_velocity": "flow_velocity negativo sin confirmar"},
        "constants": {"material_type": "gas", "gravity_level": 0},
        "notes_from": ["Nozzle (mm)", "Fuel Rate (sccm)", "Fuel Rate (mg/s)",
                       "HC Fuel Rate (mg/s)", "GMT Flame Off"],
    },
    "PSI_39/PSI-39_tabla.csv": {
        "id_columns": ["Flex Number"],
        "drop_exact_duplicates": True,
        "text": {"material_or_fuel": "Fuel"},
        "numeric": {"o2_percent": ("Oxygen", 100)},                   # fracción -> %
        "pressure_text": {"pressure_kpa": "Pressure"},                # "1 atm" -> kPa
        "constants": {"material_type": "líquido", "gravity_level": 0},
        "notes_from": ["Test Date", "CIR", "Fiber", "Nitrogen", "Helium"],  # N2 y He, fracción
    },
    "PSI_99/PSI-99_tabla.csv": {
        "id_columns": ["Sample Number"],
        "id_regex": r"^\d+-\d+$",
        "ffill_columns": ["Material"],
        "text": {"material_or_fuel": "Material"},
        "numeric_extract": {
            "o2_percent": ("Percent O2 (Note 1)", 1),                 # "~ 22.1" -> 22.1
            "flow_velocity": ("Air Flow (cm/s)", 1),                  # "20 cm/s" -> 20.0
        },
        "mapped": {
            "flame_outcome": ("?-g Burn Length", PSI_99_OUTCOME_MAP),
        },
        "constants": {"material_type": "sólido", "gravity_level": 0},
        "spread_rate": {
            "column": "?-g Spread Length",
            "factor": 1,
            "unit": "mm/s",
            "extract": True,                                          # "2.1 mm/s" -> 2.1; "Note 4" -> NaN
        },
        "notes_from": [
            "Samle Thickness", "Sample Length", "Sample Width (cm)",
            "Percent O2 (Note 1)", "Ignition Power (W)", "Ignition Time (s)",
            "Burn Time (s)", "Flow Direction", "?-g Burn Length",
            "?-g Spread Length", "1-g Burn Length", "1-g Spread Rate",
            "Camera 1", "Camera 2",
        ],
    },
    # PSI_22: fuera por ahora (su tabla es por día de pruebas, no por ensayo).
}


def clean_text(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip().str.lower()
    return s.str.replace(r"\s+", " ", regex=True).str.replace(r"\s+%", "%", regex=True)


def extract_leading_number(s: pd.Series) -> pd.Series:
    extracted = s.astype("string").str.extract(r"^\s*~?\s*([+-]?\d+(?:\.\d+)?)")[0]
    return pd.to_numeric(extracted, errors="coerce")


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
    if "id_regex" in spec:
        df = df[df[id_cols[0]].astype("string").str.strip().str.match(spec["id_regex"])].copy()
    for col in spec.get("ffill_columns", []):
        if col in df.columns:
            df[col] = df[col].ffill()
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

    for target, (col, factor) in spec.get("numeric_extract", {}).items():
        out[target] = extract_leading_number(df[col]) * factor
        warn_lost(key, col, df[col], out[target])

    for target in spec.get("blank_negative", []):
        neg = out[target] < 0
        if neg.any():
            print(f"[aviso] {key}: {int(neg.sum())} negativos de {target} quedan vacíos")
            out.loc[neg, target] = float("nan")

    extra_notes = {}
    for target, msg in spec.get("flag_negative", {}).items():
        neg = out[target] < 0
        for idx in out.index[neg]:
            extra_notes.setdefault(idx, []).append(msg)
        if neg.any():
            print(f"[aviso] {key}: {int(neg.sum())} filas con {target} negativo marcadas en notes")

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
        series = (
            extract_leading_number(df[s["column"]])
            if s.get("extract")
            else pd.to_numeric(df[s["column"]], errors="coerce")
        )
        out["flame_spread_rate"] = series * s.get("factor", 1)
        out["spread_rate_unit"] = s["unit"]

    missing = [c for c in spec.get("notes_from", []) if c not in df.columns]
    if missing:
        print(f"[aviso] {key}: columnas de notes_from que no existen: {missing}")
    cols = [c for c in spec.get("notes_from", []) if c in df.columns]

    def build_note(row):
        parts = [f"{c.strip()}={str(row[c]).strip()}" for c in cols
                 if pd.notna(row[c]) and str(row[c]).strip() not in ("", "-")]
        parts += extra_notes.get(row.name, [])
        parts += spec.get("notes_const", [])
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


def _norm_key(key: str) -> str:
    """'PSI_101/PSI-101-tabla.csv' y 'PSI_101/PSI-101_tabla.csv' dan la misma llave."""
    return re.sub(r"[\s_\-]+", "_", key).lower()


def build_master() -> pd.DataFrame:
    specs = {_norm_key(k): v for k, v in SPECS.items()}
    parts = []
    for key, df in ingest().items():
        spec = specs.get(_norm_key(key))
        if spec is None:
            print(f"[aviso] sin spec, se omite: {key}")
            continue
        parts.append(normalize_table(key, df, spec))
    if not parts:
        raise SystemExit("[ERROR] ningún CSV coincide con SPECS. Revisa las llaves.")
    master = pd.concat(parts, ignore_index=True)
    master = make_ids_unique(master)
    # Si hay velocidad de propagación medida, la llama propagó
    if "flame_spread_rate" in master:
        prop = master["flame_spread_rate"].notna() & master["flame_outcome"].isna()
        master.loc[prop, "flame_outcome"] = "propagó"
    master = master.merge(load_catalog(), on="psi_id", how="left")
    master = master.reindex(columns=MASTER_COLUMNS)  # lo que falta queda vacío, nunca 0
    # La unidad solo acompaña a un valor: sin velocidad de propagación, sin unidad
    master.loc[master["flame_spread_rate"].isna(), "spread_rate_unit"] = pd.NA
    return master


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