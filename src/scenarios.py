"""scenarios.py — Escenarios de misión, conteos por gravedad y revisión de la tabla maestra.

Space Challenge · rol Python 2. Módulo NUEVO: no cambia ninguna firma del contrato
(`rank`, `coverage_grid`); solo agrega funciones que Dev A puede conectar.

Los escenarios («Base lunar», «Traje espacial», «ISS / Tierra») se definen UNA sola vez,
en `SCENARIOS`, con su fuente. Todo lo demás (relevancia, conteos, celdas del mapa)
lee de ahí.

Funciones para Dev A (firmas):
    SCENARIOS                              dict nombre -> Scenario (o2, pressure_kpa, gravity, source)
    scenario_counts(df)                    -> DataFrame: cuántos ensayos caen en cada escenario
    gravity_counts(df)                     -> DataFrame: conteos por microgravedad / parcial / normal
    rank_scenario(df, weights, scenario)   -> igual que `rank`, con la relevancia del escenario
    scenario_cells(scenario)               -> celdas de coverage_grid que toca el escenario (rectángulo)
    check_master(df)                       -> DataFrame con problemas de la tabla maestra

Revisar una tabla real desde la terminal (raíz del repo):
    python -m src.scenarios data/processed/master_table.csv
"""
from __future__ import annotations

import sys
import unicodedata
from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd

try:  # como paquete (src.scenarios) o suelto
    from .coverage import DEFAULT_BINS, _bin_labels
    from .ranking import RANK_WEIGHT_KEYS, _rank_weights, rank
except ImportError:  # pragma: no cover
    from coverage import DEFAULT_BINS, _bin_labels  # type: ignore
    from ranking import RANK_WEIGHT_KEYS, _rank_weights, rank  # type: ignore

__all__ = [
    "Scenario", "SCENARIOS", "get_scenario", "GRAVITY_CATEGORIES", "classify_gravity",
    "gravity_counts", "scenario_mask", "scenario_counts", "scenario_relevance",
    "rank_scenario", "scenario_cells", "check_master", "EXPECTED_COLUMNS",
]

# ---------------------------------------------------------------------------
# Gravedad. Fuente de los valores de referencia: NASA/TM-1998-207417 (Friedman),
# https://ntrs.nasa.gov/api/citations/19980209743/downloads/19980209743.pdf
# (Marte ≈ 0.38 g, Luna ≈ 0.16 g, "gravedad parcial"; microgravedad = fracciones muy pequeñas de g).
# Los UMBRALES de abajo son SUPUESTO DEL EQUIPO (ningún estándar los fija así).
# `gravity_level` debe venir en g (1 = Tierra).
# ---------------------------------------------------------------------------
GRAVITY_MICRO_MAX_G = 0.01      # g < 0.01            -> microgravedad
GRAVITY_NORMAL_MIN_G = 0.9      # 0.01 <= g < 0.9     -> parcial; g >= 0.9 -> normal
GRAVITY_MAX_VALID_G = 2.0       # g > 2 -> "sin clasificar" (¿unidades distintas, p. ej. m/s²?)

MICRO, PARTIAL, NORMAL = "microgravedad", "parcial", "normal"
UNCLASSIFIED, MISSING = "sin clasificar", "sin dato"
GRAVITY_CATEGORIES = (MICRO, PARTIAL, NORMAL, UNCLASSIFIED, MISSING)

_MICRO_WORDS = ("micro", "zero", "cero", "weightless", "ingrav")
_PARTIAL_WORDS = ("partial", "parcial", "reduc", "lunar", "luna", "moon", "mars", "marte")
_NORMAL_WORDS = ("normal", "earth", "tierra", "terrestre", "ground", "1g", "1 g", "1-g")


def _norm_text(value) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return text.strip().lower()


def _category_from_g(g: float) -> str:
    if not np.isfinite(g) or g < 0 or g > GRAVITY_MAX_VALID_G:
        return UNCLASSIFIED
    if g < GRAVITY_MICRO_MAX_G:
        return MICRO
    return PARTIAL if g < GRAVITY_NORMAL_MIN_G else NORMAL


def _gravity_category(value) -> str:
    if pd.isna(value):
        return MISSING
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
        return _category_from_g(float(value))
    text = _norm_text(value)
    for words, label in ((_MICRO_WORDS, MICRO), (_PARTIAL_WORDS, PARTIAL), (_NORMAL_WORDS, NORMAL)):
        if any(w in text for w in words):
            return label
    try:
        return _category_from_g(float(text.replace("g", "").replace(",", ".").strip()))
    except ValueError:
        return UNCLASSIFIED


def classify_gravity(values: pd.Series) -> pd.Series:
    """Cada valor de `gravity_level` -> microgravedad / parcial / normal / sin clasificar / sin dato."""
    return values.map(_gravity_category)


def _require(df: pd.DataFrame, columns) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"Faltan columnas en df: {missing}")


def gravity_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Conteos por tipo de gravedad (para las tarjetas). Siempre trae las 5 categorías,
    incluso con 0: un 0 en «parcial» es un vacío real, y «sin dato» se cuenta aparte."""
    _require(df, ["gravity_level"])
    cat = classify_gravity(df["gravity_level"])
    rows = []
    for c in GRAVITY_CATEGORIES:
        m = cat == c
        n_inv = int(df.loc[m, "psi_id"].nunique()) if "psi_id" in df.columns else None
        rows.append({"categoria": c, "n_ensayos": int(m.sum()), "n_investigaciones": n_inv})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Escenarios (UN solo lugar). Rangos inclusivos.
# Los centros salen de fuentes NASA; los márgenes alrededor son SUPUESTO DEL EQUIPO.
# ---------------------------------------------------------------------------
_NTRS = "https://ntrs.nasa.gov/api/citations/"


@dataclass(frozen=True)
class Scenario:
    name: str
    o2: tuple[float, float]              # % de oxígeno (mín, máx)
    pressure_kpa: tuple[float, float]    # kPa (mín, máx)
    gravity: tuple[str, ...] | None      # categorías de gravedad que cuentan; None = cualquiera
    source: str


SCENARIOS: dict[str, Scenario] = {
    "Base lunar": Scenario(
        "Base lunar", o2=(26.5, 34.0), pressure_kpa=(56.5, 70.3), gravity=(PARTIAL,),
        source=("Atmósfera de exploración 8.2 psia (56.5 kPa) / 34 % O2 y alternativa 10.2 psia "
                f"(70.3 kPa) / 26.5 % O2: {_NTRS}20220005709/downloads/"
                "AsMA%202022%20-%20Abercromby%20-%20DCS%20Strategic%20Plan%20v2.pdf y "
                f"{_NTRS}20240005117/downloads/ICES-2024-128-Final%20Manuscript-No%20Tracked%20Changes.pdf. "
                "Gravedad lunar ≈ 0.16 g (parcial): NASA/TM-1998-207417. "
                "El rango entre ambas atmósferas es supuesto del equipo."),
    ),
    "Traje espacial": Scenario(
        "Traje espacial", o2=(85.0, 100.0), pressure_kpa=(25.0, 35.0), gravity=None,
        source=(f"Presión de traje 4.3 psia ≈ 29.6 kPa y 85 % O2 en EVA simulada: {_NTRS}20240005151/downloads/"
                f"2024_05_06_Garbino_EA_final.pdf y {_NTRS}20220016245/downloads/AsMA_exploration_prebreathe_10-20-22.pdf. "
                "Los márgenes (85–100 % O2, 25–35 kPa) y aceptar cualquier gravedad (EVA en órbita y en superficie) "
                "son supuesto del equipo."),
    ),
    "ISS / Tierra": Scenario(
        "ISS / Tierra", o2=(19.0, 23.0), pressure_kpa=(95.0, 105.0), gravity=None,
        source=(f"Atmósfera a nivel del mar 21 % O2 / 14.7 psia (101.35 kPa) usada en ISS: {_NTRS}20240005117/downloads/"
                "ICES-2024-128-Final%20Manuscript-No%20Tracked%20Changes.pdf. "
                "Los márgenes (±2 puntos de O2, ±5 kPa) y aceptar cualquier gravedad son supuesto del equipo."),
    ),
}


def get_scenario(scenario: str | Scenario) -> Scenario:
    if isinstance(scenario, Scenario):
        return scenario
    if scenario not in SCENARIOS:
        raise KeyError(f"Escenario desconocido: {scenario!r}. Válidos: {list(SCENARIOS)}")
    return SCENARIOS[scenario]


def _numeric(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce")


def scenario_mask(df: pd.DataFrame, scenario: str | Scenario, use_gravity: bool = True) -> pd.Series:
    """True para los ensayos dentro del escenario. Sin O2 o presión nunca entran."""
    sc = get_scenario(scenario)
    _require(df, ["o2_percent", "pressure_kpa"] + (["gravity_level"] if use_gravity and sc.gravity else []))
    mask = _numeric(df, "o2_percent").between(*sc.o2) & _numeric(df, "pressure_kpa").between(*sc.pressure_kpa)
    if use_gravity and sc.gravity:
        mask &= classify_gravity(df["gravity_level"]).isin(sc.gravity)
    return mask


def scenario_counts(df: pd.DataFrame, scenarios: Mapping[str, Scenario] | None = None) -> pd.DataFrame:
    """Cuántos ensayos caen dentro de cada escenario.

    n_atmosfera            ensayos con O2 y presión dentro del rango
    n_atmosfera_y_gravedad además cumplen la gravedad del escenario (si la pide)
    estado                 'cubierto' o 'VACÍO: ...' (p. ej. «0 ensayos en gravedad parcial»)
    """
    _require(df, ["o2_percent", "pressure_kpa", "gravity_level"])
    no_conditions = int((df["o2_percent"].isna() | df["pressure_kpa"].isna()).sum())
    rows = []
    for name, sc in (SCENARIOS if scenarios is None else scenarios).items():
        n_atm = int(scenario_mask(df, sc, use_gravity=False).sum())
        full = scenario_mask(df, sc, use_gravity=True)
        n_full = int(full.sum())
        grav = " / ".join(sc.gravity) if sc.gravity else "cualquiera"
        if n_atm == 0:
            estado = "VACÍO: 0 ensayos con esta atmósfera"
        elif sc.gravity and n_full == 0:
            estado = f"VACÍO: {n_atm} ensayos con esta atmósfera, pero 0 en gravedad {grav}"
        else:
            estado = "cubierto"
        rows.append({
            "escenario": name, "gravedad": grav,
            "n_atmosfera": n_atm, "n_atmosfera_y_gravedad": n_full,
            "n_investigaciones": int(df.loc[full, "psi_id"].nunique()) if "psi_id" in df.columns else None,
            "n_sin_dato": no_conditions, "estado": estado,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Relevancia por escenario. Mismas escalas que build_features (hay una prueba que lo vigila).
# La gravedad NO entra a la relevancia (casi todo es microgravedad y todo daría 0):
# se reporta aparte en scenario_counts / gravity_counts.  Supuesto del equipo.
# ---------------------------------------------------------------------------
O2_SCALE = 20.0
P_SCALE = 50.0


def _excess(x: pd.Series, lo: float, hi: float) -> pd.Series:
    """Distancia al rango [lo, hi]: 0 dentro, NaN si falta el dato."""
    return np.maximum(np.maximum(lo - x, x - hi), 0.0)


def scenario_relevance(df: pd.DataFrame, scenario: str | Scenario) -> pd.Series:
    """1 = dentro del escenario; baja linealmente hasta 0 a 20 puntos de O2 / 50 kPa. Faltante = 0."""
    sc = get_scenario(scenario)
    _require(df, ["o2_percent", "pressure_kpa"])
    d = np.hypot(_excess(_numeric(df, "o2_percent"), *sc.o2) / O2_SCALE,
                 _excess(_numeric(df, "pressure_kpa"), *sc.pressure_kpa) / P_SCALE)
    return (1 - d).clip(lower=0.0, upper=1.0).fillna(0.0)


def rank_scenario(df: pd.DataFrame, weights: Mapping[str, float], scenario: str | Scenario) -> pd.DataFrame:
    """Igual que `rank` (mismas columnas, mismo orden), pero score_relevancia mide la cercanía
    al escenario elegido y score_total se recalcula con ese valor. Los otros tres
    componentes no cambian."""
    w = _rank_weights(weights)
    out = rank(df, weights)
    out["score_relevancia"] = scenario_relevance(df, scenario).to_numpy()
    out["score_total"] = sum(w[k] * out[f"score_{k}"] for k in RANK_WEIGHT_KEYS)
    return out


def scenario_cells(scenario: str | Scenario) -> dict[str, list[str]]:
    """Etiquetas de `coverage_grid` que toca el escenario: {"presion": [...], "oxigeno": [...]}.

    Sirve para dibujar el rectángulo sobre el mapa: va de la primera a la última etiqueta
    de cada lista (se ajusta a los rangos de la rejilla, es una aproximación del rectángulo real)."""
    sc = get_scenario(scenario)

    def overlap(col: str, box: tuple[float, float]) -> list[str]:
        edges = DEFAULT_BINS[col]
        return [lab for lab, (a, b) in zip(_bin_labels(edges), zip(edges[:-1], edges[1:]))
                if a <= box[1] and b > box[0]]

    return {"presion": overlap("pressure_kpa", sc.pressure_kpa), "oxigeno": overlap("o2_percent", sc.o2)}


# ---------------------------------------------------------------------------
# Revisión de la tabla maestra real (contrato de Python 1)
# ---------------------------------------------------------------------------
EXPECTED_COLUMNS = [
    "experiment_id", "psi_id", "doi", "license", "title", "material_or_fuel", "material_type",
    "o2_percent", "pressure_kpa", "flow_velocity", "gravity_level", "flame_outcome",
    "flame_spread_rate", "spread_rate_unit", "source_file", "source_page", "notes",
]
_KNOWN_OUTCOME_WORDS = ("propag", "extin", "otro", "other")


def check_master(df: pd.DataFrame) -> pd.DataFrame:
    """Busca problemas que los datos reales suelen traer. No modifica nada.

    Devuelve: severidad ('error' | 'aviso'), columna, problema, n_filas, ejemplos."""
    issues: list[dict] = []
    ids = df["experiment_id"].astype(str) if "experiment_id" in df.columns else pd.Series(df.index.astype(str), index=df.index)

    def add(severity: str, column: str, problem: str, mask: pd.Series | None = None, n: int | None = None):
        count = int(mask.sum()) if mask is not None else (len(df) if n is None else n)
        if count == 0:
            return
        examples = ", ".join(ids[mask].head(3)) if mask is not None else ""
        issues.append({"severidad": severity, "columna": column, "problema": problem,
                       "n_filas": count, "ejemplos": examples})

    for c in EXPECTED_COLUMNS:
        if c not in df.columns:
            add("error", c, "falta la columna del contrato")
    extra = [c for c in df.columns if c not in EXPECTED_COLUMNS]
    if extra:
        add("aviso", ", ".join(extra), "columnas que no están en el contrato", n=len(df))
    present = [c for c in EXPECTED_COLUMNS if c in df.columns]
    if not [c for c in EXPECTED_COLUMNS if c not in df.columns] and list(df.columns[:len(EXPECTED_COLUMNS)]) != EXPECTED_COLUMNS:
        add("aviso", "(orden)", "las columnas no están en el orden del contrato")

    if "experiment_id" in present:
        add("error", "experiment_id", "experiment_id repetido", df["experiment_id"].duplicated(keep=False) & df["experiment_id"].notna())
    if "psi_id" in present:
        add("error", "psi_id", "ensayo sin psi_id", df["psi_id"].isna())
    for c in ("doi", "license"):
        if c in present:
            add("aviso", c, "vacío (debe salir de data/catalog.csv)", df[c].isna())

    nums = {}
    for c in ("o2_percent", "pressure_kpa", "flow_velocity", "flame_spread_rate"):
        if c in present:
            nums[c] = pd.to_numeric(df[c], errors="coerce")
            add("error", c, "valores que no son números", df[c].notna() & nums[c].isna())
    if "o2_percent" in nums:
        x = nums["o2_percent"]
        add("error", "o2_percent", "fuera de 0–100 %", (x < 0) | (x > 100))
        add("aviso", "o2_percent", "es 0: probable dato faltante escrito como 0 (debe ir vacío)", x == 0)
    if "pressure_kpa" in nums:
        x = nums["pressure_kpa"]
        add("error", "pressure_kpa", "presión negativa", x < 0)
        add("aviso", "pressure_kpa", "es 0: probable dato faltante escrito como 0 (debe ir vacío)", x == 0)
        add("aviso", "pressure_kpa", "mayor de 300 kPa: ¿unidades equivocadas?", x > 300)
    if "flow_velocity" in nums:
        add("error", "flow_velocity", "velocidad de flujo negativa", nums["flow_velocity"] < 0)
    if "flame_spread_rate" in nums:
        add("error", "flame_spread_rate", "tasa de propagación negativa", nums["flame_spread_rate"] < 0)
        if "spread_rate_unit" in present:
            has_rate = nums["flame_spread_rate"].notna()
            units = sorted(df.loc[has_rate, "spread_rate_unit"].dropna().astype(str).unique())
            if len(units) > 1:
                add("aviso", "spread_rate_unit", f"unidades mezcladas {units}: flame_spread_rate no es comparable", has_rate)
            add("aviso", "spread_rate_unit", "hay tasa de propagación sin unidad", has_rate & df["spread_rate_unit"].isna())

    if "flame_outcome" in present:
        text = df["flame_outcome"].map(lambda v: _norm_text(v) if pd.notna(v) else None)
        unknown = text.notna() & ~text.fillna("").apply(lambda t: any(w in t for w in _KNOWN_OUTCOME_WORDS))
        add("aviso", "flame_outcome", "valor no reconocido: el ranking lo cuenta como «otro» (0.5)", unknown)
    if "gravity_level" in present:
        cat = classify_gravity(df["gravity_level"])
        add("aviso", "gravity_level", "no se pudo clasificar (¿no está en g?)", cat == UNCLASSIFIED)
    if {"o2_percent", "pressure_kpa"} <= set(present):
        add("aviso", "o2_percent / pressure_kpa", "sin O2 ni presión: no entra a cobertura y su relevancia es 0",
            df["o2_percent"].isna() & df["pressure_kpa"].isna())

    out = pd.DataFrame(issues, columns=["severidad", "columna", "problema", "n_filas", "ejemplos"])
    order = out["severidad"].map({"error": 0, "aviso": 1})
    return out.assign(_o=order).sort_values("_o", kind="stable").drop(columns="_o").reset_index(drop=True)


def main(path: str = "data/processed/master_table.csv") -> None:
    df = pd.read_csv(path)
    pd.set_option("display.width", 200, "display.max_colwidth", 80)
    print(f"{len(df)} filas, {df['psi_id'].nunique() if 'psi_id' in df.columns else '?'} investigaciones\n")
    issues = check_master(df)
    print("== Problemas de la tabla ==")
    print("sin problemas" if issues.empty else issues.to_string(index=False))
    print("\n== Gravedad ==")
    print(gravity_counts(df).to_string(index=False))
    print("\n== Escenarios ==")
    print(scenario_counts(df).drop(columns="gravedad").to_string(index=False))


if __name__ == "__main__":  # pragma: no cover
    main(*sys.argv[1:2])