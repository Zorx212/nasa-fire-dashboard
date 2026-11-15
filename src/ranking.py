"""ranking.py — Ranking explicable de experimentos de combustión en microgravedad.

Space Challenge · rol Python 2 (ranking y análisis).

CONTRATO con Dev A (firma exacta):

    rank(df, weights) -> df (mismas filas) + score_relevancia, score_riesgo,
                         score_evidencia, score_cobertura, score_total  (todos 0–1)

    weights = {"relevancia": ., "riesgo": ., "evidencia": ., "cobertura": .}
    (se normalizan solos; el desglose por componente: `rank_contributions`).

Idea central
------------
    puntaje = Σ ( peso_i × valor_normalizado_i )

Cada criterio aporta "puntos" (su contribución), así que el ranking se explica
solo: se puede mostrar el desglose y decir por qué un experimento va primero.

Los cuatro criterios (plan §9) se calculan a partir de la tabla maestra (plan §8):

    relevancia          cercanía a las condiciones de cabina (Luna/Marte, ISS)
    riesgo_propagacion  proporción de ensayos donde la llama propagó
    evidencia           nº de ensayos + completitud de datos y citas
    cobertura           nº de condiciones distintas (O2, presión, flujo) exploradas

Además de `rank` (una fila por experimento), `rank_master` agrega por
investigación PSI y trae filtros, explicación en texto y gráficas Plotly.

Uso rápido (Jupyter o Streamlit)
--------------------------------
    import pandas as pd
    from src.ranking import rank, rank_master, explain_item, compare_items, plot_ranking

    master = pd.read_csv("data/processed/master_table.csv")
    ranked = rank(master, {"relevancia": .35, "riesgo": .2, "evidencia": .25, "cobertura": .2})

    scored, criteria = rank_master(
        master,
        weights={"relevancia": 0.4, "evidencia": 0.3},      # opcional, ajustable
        filters={"material_type": ["sólido"], "o2_range": (21, 40)},  # opcional
    )
    scored[["rank", "psi_id", "score"]]
    explain_item(scored, "PSI-159", criteria, id_col="psi_id")
    plot_ranking(scored, criteria, id_col="psi_id")           # -> figura Plotly

Importante: importar como `src.ranking` (no `import coverage` suelto, que choca
con el paquete `coverage` de pytest-cov).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

__all__ = [
    "Criterion", "DEFAULT_CRITERIA", "DEFAULT_REFERENCES", "MASTER_COLS",
    "RANK_WEIGHT_KEYS", "N_TRIALS_FULL",
    "criteria_from_dict", "apply_filters", "build_features", "normalize",
    "score_items", "rank_master", "weights_table", "explain_item",
    "compare_items", "weight_sensitivity", "plot_ranking", "plot_comparison",
    "plot_condition_ranges", "rank", "rank_contributions",
]

# ---------------------------------------------------------------------------
# Configuración (todo editable)
# ---------------------------------------------------------------------------

# Nombres de columna de la tabla maestra (plan §8). Si Python 1 usa otros,
# pásalos en el argumento `cols=` de las funciones, sin tocar el código.
MASTER_COLS = {
    "investigation_id": "psi_id",
    "experiment_id": "experiment_id",
    "title": "title",
    "doi": "doi",
    "material": "material_or_fuel",
    "material_type": "material_type",
    "o2": "o2_percent",
    "pressure": "pressure_kpa",
    "flow": "flow_velocity",
    "outcome": "flame_outcome",
    "spread": "flame_spread_rate",
    "page": "source_page",
}

# Ensayos a partir de los cuales una investigación ya cuenta con "evidencia completa".
N_TRIALS_FULL = 10

# Condiciones de referencia para "relevancia". SUPUESTO a confirmar con el
# equipo: la atmósfera de exploración que se cita para Luna/Marte (≈34 % O2 a
# 56.5 kPa ≈ 8.2 psia) y la cabina de la ISS (≈21 % O2 a 101.3 kPa).
DEFAULT_REFERENCES = {
    "Luna/Marte (atmósfera de exploración)": {"o2_percent": 34.0, "pressure_kpa": 56.5},
    "ISS (cabina actual)": {"o2_percent": 21.0, "pressure_kpa": 101.3},
}

# Paleta categórica validada (orden fijo, nunca ciclada) y tintas del tema claro.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
               "#e87ba4", "#008300", "#6250d6", "#e34948"]
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


@dataclass(frozen=True)
class Criterion:
    """Un criterio del puntaje: columna, peso, sentido y escala.

    scale (cómo pasar el valor a 0–1; None = usar el `method` global):
      "unit"       el valor ya va de 0 a 1 y puntúa tal cual (0.43 -> 43 % del peso)
      "max"        valor / máximo (un conteo: 3 de 10 -> 30 % del peso)
      "minmax"     relativo: el peor = 0 y el mejor = 1
      "percentile" por posición, robusto a valores extremos
    """
    column: str
    weight: float = 1.0
    higher_is_better: bool = True
    label: str | None = None
    scale: str | None = None

    @property
    def name(self) -> str:
        return self.label or self.column


# Pesos iniciales (se normalizan solos para sumar 1). Ajustables en la interfaz.
# Interpretación: "riesgo" alto = el experimento informa más sobre el peligro,
# por eso sube en el ranking. Decisión de equipo: se puede invertir con
# higher_is_better=False.
DEFAULT_CRITERIA = (
    Criterion("relevancia", 0.35, True, "Relevancia Luna/Marte", scale="unit"),
    Criterion("riesgo_propagacion", 0.20, True, "Riesgo de propagación observado", scale="unit"),
    Criterion("evidencia", 0.25, True, "Calidad de la evidencia", scale="unit"),
    Criterion("cobertura", 0.20, True, "Cobertura de condiciones", scale="max"),
)


def criteria_from_dict(spec: Mapping[str, Mapping | float]) -> list[Criterion]:
    """{"col": 0.3, "otra": {"weight": 0.2, "higher_is_better": False}} -> [Criterion]."""
    out = []
    for col, v in spec.items():
        out.append(Criterion(col, **v) if isinstance(v, Mapping) else Criterion(col, weight=float(v)))
    return out


def _resolve(criteria=None, weights: Mapping[str, float] | None = None) -> list[Criterion]:
    if criteria is None:
        criteria = DEFAULT_CRITERIA
    crit = criteria_from_dict(criteria) if isinstance(criteria, Mapping) else list(criteria)
    if weights:
        cols = {c.column for c in crit}
        unknown = set(weights) - cols
        if unknown:
            raise KeyError(f"Pesos para criterios que no existen: {sorted(unknown)}. Válidos: {sorted(cols)}")
        crit = [dataclasses.replace(c, weight=float(weights[c.column])) if c.column in weights else c
                for c in crit]
    return crit


def _norm_weights(criteria: Sequence[Criterion]) -> dict[str, float]:
    total = sum(c.weight for c in criteria)
    return {c.column: c.weight / total for c in criteria}


def _check(df: pd.DataFrame, criteria: Sequence[Criterion], id_col: str | None = None) -> None:
    if not criteria:
        raise ValueError("Define al menos un criterio.")
    cols = [c.column for c in criteria]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Columnas no encontradas en la tabla: {missing}")
    if len(set(cols)) != len(cols):
        raise ValueError("Hay criterios repetidos.")
    if len({c.name for c in criteria}) != len(criteria):
        raise ValueError("Las etiquetas de los criterios deben ser únicas.")
    if any(c.weight < 0 for c in criteria):
        raise ValueError("Los pesos no pueden ser negativos.")
    if sum(c.weight for c in criteria) <= 0:
        raise ValueError("La suma de pesos debe ser mayor que 0.")
    if id_col is not None:
        if id_col not in df.columns:
            raise KeyError(f"No existe la columna de identificador '{id_col}'.")
        if df[id_col].duplicated().any():
            raise ValueError(f"'{id_col}' tiene valores repetidos; agrega por entidad antes de rankear.")


# ---------------------------------------------------------------------------
# Filtros (pantalla Ranking: material, oxígeno, presión, flujo)
# ---------------------------------------------------------------------------

def apply_filters(master: pd.DataFrame, material_type=None, material=None,
                  o2_range=None, pressure_range=None, flow_range=None,
                  keep_missing: bool = False, cols: Mapping[str, str] | None = None) -> pd.DataFrame:
    """Filtra ensayos de la tabla maestra.

    Los rangos son (mín, máx) inclusivos. Un ensayo sin dato en la variable
    filtrada se excluye, salvo `keep_missing=True` (no se puede confirmar que cumpla).
    """
    c = {**MASTER_COLS, **(cols or {})}
    mask = pd.Series(True, index=master.index)
    for key, values in (("material_type", material_type), ("material", material)):
        if values is not None:
            if isinstance(values, str):
                values = [values]
            mask &= master[c[key]].isin(list(values))
    for key, rng in (("o2", o2_range), ("pressure", pressure_range), ("flow", flow_range)):
        if rng is not None:
            lo, hi = rng
            x = pd.to_numeric(master[c[key]], errors="coerce")
            ok = x.between(lo, hi)
            mask &= (ok | x.isna()) if keep_missing else ok
    return master[mask]


# ---------------------------------------------------------------------------
# De la tabla maestra a los criterios
# ---------------------------------------------------------------------------

def _relevance(o2: pd.Series, p: pd.Series, references: Mapping[str, Mapping[str, float]],
               o2_scale: float, p_scale: float) -> pd.Series:
    """1 = justo en una condición de referencia; 0 = a `scale` o más de distancia."""
    best = pd.Series(np.nan, index=o2.index)
    for ref in references.values():
        d = np.hypot((o2 - ref["o2_percent"]) / o2_scale, (p - ref["pressure_kpa"]) / p_scale)
        best = np.fmax(best, (1 - d).clip(lower=0))  # fmax ignora NaN
    return best


def _text_join(s: pd.Series, limit: int = 3) -> str | None:
    vals = s.dropna().astype(str).unique()
    return "; ".join(vals[:limit]) if len(vals) else None


def _type_label(s: pd.Series) -> str | None:
    vals = s.dropna().astype(str).unique()
    if not len(vals):
        return None
    return vals[0] if len(vals) == 1 else "mixto"


def build_features(master: pd.DataFrame, level: str = "investigation",
                   references: Mapping[str, Mapping[str, float]] | None = None,
                   cols: Mapping[str, str] | None = None,
                   o2_scale: float = 20.0, p_scale: float = 50.0,
                   n_trials_full: int = N_TRIALS_FULL, relevance_agg: str = "max") -> pd.DataFrame:
    """Calcula los cuatro criterios a partir de la tabla maestra.

    level="investigation": una fila por investigación PSI (lo normal para 5–8 PSI).
    level="experiment":    una fila por ensayo (usa la cobertura de su investigación).

    Faltantes: se quedan como NaN (nunca como 0); `score_items` decide cuánto
    puntúan y reporta la completitud.
    """
    if level not in ("investigation", "experiment"):
        raise ValueError("level debe ser 'investigation' o 'experiment'.")
    c = {**MASTER_COLS, **(cols or {})}
    refs = DEFAULT_REFERENCES if references is None else references
    gid, o2c, pc = c["investigation_id"], c["o2"], c["pressure"]
    missing = [x for x in (gid, o2c, pc) if x not in master.columns]
    if missing:
        raise KeyError(f"Faltan columnas obligatorias en la tabla maestra: {missing}")

    df = master.copy()
    for k in ("o2", "pressure", "flow", "spread"):
        if c[k] in df.columns:
            df[c[k]] = pd.to_numeric(df[c[k]], errors="coerce")

    df["relevancia"] = _relevance(df[o2c], df[pc], refs, o2_scale, p_scale)

    risk = pd.Series(np.nan, index=df.index)
    if c["outcome"] in df.columns:
        s = df[c["outcome"]].astype("string").str.lower()
        risk[s.str.contains("propag", na=False)] = 1.0
        risk[s.str.contains(r"\b(?:no|not|sin)\s+propag", na=False)] = 0.0   # "no propagó"
        risk[s.str.contains("extin", na=False)] = 0.0
        risk[s.notna() & risk.isna()] = 0.5          # "otro"
    df["riesgo_propagacion"] = risk

    key = [c[k] for k in ("o2", "pressure", "flow", "outcome", "spread", "page", "doi") if c[k] in df.columns]
    df["_completo"] = df[key].notna().mean(axis=1)

    dims = [c[k] for k in ("o2", "pressure", "flow") if c[k] in df.columns]
    combos = df.dropna(subset=dims, how="all").drop_duplicates([gid] + dims).groupby(gid).size()
    df["cobertura"] = df[gid].map(combos).fillna(0)

    if level == "experiment":
        eid = c["experiment_id"]
        if eid not in df.columns:
            df[eid] = df.index.astype(str)
        return df.rename(columns={"_completo": "evidencia"}).reset_index(drop=True)

    g = df.groupby(gid, sort=False)
    out = pd.DataFrame({
        "n_ensayos": g.size(),
        "relevancia": g["relevancia"].agg(relevance_agg),
        "riesgo_propagacion": g["riesgo_propagacion"].mean(),
        "completitud": g["_completo"].mean(),
        "cobertura": g["cobertura"].first(),
        "o2_min": g[o2c].min(), "o2_max": g[o2c].max(),
        "pressure_min": g[pc].min(), "pressure_max": g[pc].max(),
    })
    out["evidencia"] = 0.5 * np.minimum(out["n_ensayos"] / n_trials_full, 1.0) + 0.5 * out["completitud"]
    for key_, fn in (("title", _text_join), ("doi", _text_join),
                     ("material", _text_join), ("material_type", _type_label)):
        if c[key_] in df.columns:
            out[c[key_]] = g[c[key_]].agg(fn)
    return out.reset_index()


# ---------------------------------------------------------------------------
# Puntaje explicable
# ---------------------------------------------------------------------------

def normalize(values: pd.Series, higher_is_better: bool = True,
              method: str = "minmax", na_score: float = 0.0) -> pd.Series:
    """Lleva una columna a 0–1. Faltantes -> `na_score` (0 = penalizar, 0.5 = neutro).

    method: "unit" (ya es 0–1), "max" (valor/máximo), "minmax" o "percentile".
    """
    x = pd.to_numeric(values, errors="coerce")
    if method == "unit":
        norm = x.clip(0, 1)
    elif method == "max":
        hi = x.max()
        norm = pd.Series(0.5, index=x.index) if (pd.isna(hi) or hi <= 0) else (x / hi).clip(0, 1)
    elif method == "minmax":
        lo, hi = x.min(), x.max()
        norm = pd.Series(0.5, index=x.index) if (pd.isna(lo) or hi == lo) else (x - lo) / (hi - lo)
    elif method == "percentile":      # robusto a valores extremos
        n = x.notna().sum()
        norm = (x.rank(method="average") - 1) / (n - 1) if n > 1 else pd.Series(0.5, index=x.index)
    else:
        raise ValueError("method debe ser 'unit', 'max', 'minmax' o 'percentile'.")
    if not higher_is_better:
        norm = 1 - norm
    return norm.where(x.notna(), na_score)


def score_items(df: pd.DataFrame, criteria=None, id_col: str | None = None,
                method: str = "minmax", na_score: float = 0.0,
                weights: Mapping[str, float] | None = None) -> pd.DataFrame:
    """Puntaje 0–100 con desglose.

    Agrega por criterio: `norm__<col>` (0–1) y `contrib__<col>` (puntos), más
    `score`, `rank` (empates comparten puesto) y `completeness` (0–1, datos presentes).
    `weights` sobrescribe pesos al vuelo: {"relevancia": 0.5}.
    `method` es la escala para los criterios que no definen la suya (`Criterion.scale`).
    """
    crit = _resolve(criteria, weights)
    _check(df, crit, id_col)
    w = _norm_weights(crit)
    out = df.copy()
    total = pd.Series(0.0, index=df.index)
    for c in crit:
        norm = normalize(df[c.column], c.higher_is_better, c.scale or method, na_score)
        out[f"norm__{c.column}"] = norm
        out[f"contrib__{c.column}"] = norm * w[c.column] * 100
        total = total + out[f"contrib__{c.column}"]
    out["score"] = total
    out["completeness"] = df[[c.column for c in crit]].apply(pd.to_numeric, errors="coerce").notna().mean(axis=1)
    out["rank"] = out["score"].rank(method="min", ascending=False).astype(int)
    sort_cols = ["rank"] + ([id_col] if id_col else [])
    return out.sort_values(sort_cols, kind="stable").reset_index(drop=True)


def rank_master(master: pd.DataFrame, weights: Mapping[str, float] | None = None,
                criteria=None, level: str = "investigation",
                filters: Mapping | None = None, references=None,
                cols: Mapping[str, str] | None = None,
                method: str = "minmax", na_score: float = 0.0,
                **feature_kwargs) -> tuple[pd.DataFrame, list[Criterion]]:
    """Todo en un paso: filtrar -> criterios -> puntaje. Devuelve (scored, criterios).

    Agrega por investigación PSI (level="investigation"). Para el contrato con
    Dev A (una fila por experimento, columnas score_*), usa `rank`.
    """
    c = {**MASTER_COLS, **(cols or {})}
    df = apply_filters(master, cols=cols, **(filters or {})) if filters else master
    if df.empty:
        raise ValueError("Los filtros no dejan ningún ensayo; amplía los rangos.")
    feats = build_features(df, level=level, references=references, cols=cols, **feature_kwargs)
    crit = _resolve(criteria, weights)
    id_col = c["investigation_id"] if level == "investigation" else c["experiment_id"]
    return score_items(feats, crit, id_col, method, na_score), crit


# ---------------------------------------------------------------------------
# CONTRATO con Dev A: rank(df, weights)
# ---------------------------------------------------------------------------

RANK_WEIGHT_KEYS = ("relevancia", "riesgo", "evidencia", "cobertura")


def _rank_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Valida las claves del contrato y normaliza los pesos para que sumen 1."""
    if not isinstance(weights, Mapping) or set(weights) != set(RANK_WEIGHT_KEYS):
        got = sorted(weights) if isinstance(weights, Mapping) else type(weights).__name__
        raise ValueError(f"`weights` debe ser un diccionario con exactamente las claves "
                         f"{RANK_WEIGHT_KEYS}; recibí {got}")
    w = {k: float(weights[k]) for k in RANK_WEIGHT_KEYS}
    if not all(np.isfinite(v) and v >= 0 for v in w.values()):
        raise ValueError(f"Los pesos deben ser números finitos >= 0: {w}")
    total = sum(w.values())
    if total <= 0:
        raise ValueError("La suma de los pesos debe ser mayor que 0.")
    return {k: v / total for k, v in w.items()}


def rank(df: pd.DataFrame, weights: Mapping[str, float]) -> pd.DataFrame:
    """Contrato con Dev A. Una fila por experimento; las mismas filas y el mismo orden.

    Devuelve una copia de `df` con score_relevancia, score_riesgo, score_evidencia,
    score_cobertura y score_total, todos entre 0 y 1 (sin NaN: un dato faltante
    no suma puntaje). score_total = Σ peso_normalizado × score_componente.

    Los componentes son relativos a la tabla recibida (cobertura se divide entre la
    mayor de la tabla): calcula `rank` sobre la tabla completa y filtra después.
    Explicación de cada componente en notes/ranking_explicacion.md.
    """
    w = _rank_weights(weights)
    feats = build_features(df, level="experiment")      # KeyError si faltan psi_id / O2 / presión
    feats.index = df.index                              # build_features reinicia el índice

    gid = MASTER_COLS["investigation_id"]
    n_trials = df.groupby(gid)[gid].transform("size").fillna(1)
    top = feats["cobertura"].max()
    cobertura = feats["cobertura"] / top if top > 0 else pd.Series(0.0, index=df.index)

    parts = {
        "relevancia": feats["relevancia"].fillna(0.0),
        "riesgo": feats["riesgo_propagacion"].fillna(0.0),
        # mismo criterio que a nivel investigación: 50 % nº de ensayos, 50 % completitud
        "evidencia": 0.5 * np.minimum(n_trials / N_TRIALS_FULL, 1.0) + 0.5 * feats["evidencia"],
        "cobertura": cobertura,
    }
    out = df.copy()
    for k in RANK_WEIGHT_KEYS:
        out[f"score_{k}"] = parts[k].clip(0.0, 1.0)
    out["score_total"] = sum(w[k] * out[f"score_{k}"] for k in RANK_WEIGHT_KEYS)
    return out


def rank_contributions(ranked: pd.DataFrame, weights: Mapping[str, float]) -> pd.DataFrame:
    """Desglose para la interfaz: cuánto aporta cada componente a score_total (0–1).

    Las cuatro columnas suman score_total; sirve para barras apiladas.
    """
    w = _rank_weights(weights)
    return pd.DataFrame({k: w[k] * ranked[f"score_{k}"] for k in RANK_WEIGHT_KEYS})


def weights_table(criteria=None) -> pd.DataFrame:
    """Tabla de pesos (para mostrar en la UI junto a los controles)."""
    crit = _resolve(criteria)
    w = _norm_weights(crit)
    return pd.DataFrame({
        "criterio": [c.name for c in crit],
        "columna": [c.column for c in crit],
        "peso_%": [round(w[c.column] * 100, 1) for c in crit],
        "sentido": ["más es mejor" if c.higher_is_better else "menos es mejor" for c in crit],
    })


def _pick(scored: pd.DataFrame, id_col: str, ids: Sequence) -> pd.DataFrame:
    sub = scored[scored[id_col].isin(list(ids))].set_index(id_col)
    absent = [i for i in ids if i not in sub.index]
    if absent:
        raise KeyError(f"No están en el ranking: {absent}")
    return sub.loc[list(ids)]


def explain_item(scored: pd.DataFrame, item_id, criteria=None, id_col: str = "psi_id", top: int = 2) -> str:
    """Explicación en texto de por qué un elemento quedó en su puesto."""
    crit = _resolve(criteria)
    row = _pick(scored, id_col, [item_id]).iloc[0]
    wts = _norm_weights(crit)
    contrib = {c.column: float(row[f"contrib__{c.column}"]) for c in crit}
    order = sorted(crit, key=lambda c: contrib[c.column], reverse=True)

    def fmt(c: Criterion) -> str:
        raw = pd.to_numeric(row[c.column], errors="coerce")
        val = "sin dato" if pd.isna(raw) else f"{raw:.3g}"
        return f"{c.name} ({contrib[c.column]:.1f} de {wts[c.column] * 100:.1f} pts posibles; valor {val})"

    text = f"{item_id}: puesto {int(row['rank'])} de {len(scored)} con {row['score']:.1f} de 100 pts."
    best = order[:top]
    text += " Lo que más suma: " + "; ".join(fmt(c) for c in best) + "."
    worst = [c for c in order[::-1][:top] if c not in best]
    if worst:
        text += " Lo que menos suma: " + "; ".join(fmt(c) for c in worst) + "."
    gaps = [c.name for c in crit if pd.isna(pd.to_numeric(row[c.column], errors="coerce"))]
    if gaps:
        text += " Sin dato en: " + ", ".join(gaps) + "."
    return text


def compare_items(scored: pd.DataFrame, ids: Sequence, criteria=None, id_col: str = "psi_id") -> pd.DataFrame:
    """Contribución en puntos por criterio, lado a lado (2 o 3 elementos).

    Filas: un criterio por fila + "TOTAL (pts)" + "Puesto". Con 2 elementos
    agrega la columna "Diferencia (2º − 1º)".
    """
    crit = _resolve(criteria)
    sub = _pick(scored, id_col, ids)
    data = {str(i): [float(sub.loc[i, f"contrib__{c.column}"]) for c in crit]
            + [float(sub.loc[i, "score"]), float(sub.loc[i, "rank"])] for i in ids}
    table = pd.DataFrame(data, index=[c.name for c in crit] + ["TOTAL (pts)", "Puesto"])
    if len(ids) == 2:
        a, b = str(ids[0]), str(ids[1])
        table["Diferencia (2º − 1º)"] = table[b] - table[a]
    return table.round(2)


def weight_sensitivity(features: pd.DataFrame, criteria=None, id_col: str = "psi_id",
                       delta: float = 0.25, top_k: int = 10, method: str = "minmax",
                       na_score: float = 0.0) -> pd.DataFrame:
    """¿Qué tan estable es el ranking? Sube y baja cada peso `delta` (25 %) y
    mira cuánto se mueve cada elemento del top_k. `cambio_max` = mayor salto de puesto."""
    crit = _resolve(criteria)
    base = score_items(features, crit, id_col, method, na_score)
    ranks = {"base": base.set_index(id_col)["rank"]}
    for c in crit:
        for sign, tag in ((1, "+"), (-1, "−")):
            w = {k.column: k.weight for k in crit}
            w[c.column] = max(0.0, w[c.column] * (1 + sign * delta))
            if sum(w.values()) <= 0:
                continue
            s = score_items(features, crit, id_col, method, na_score, weights=w)
            ranks[f"{c.name} {tag}{round(delta * 100)}%"] = s.set_index(id_col)["rank"]
    table = pd.DataFrame(ranks).loc[base[id_col].head(top_k)]
    table["cambio_max"] = table.drop(columns="base").sub(table["base"], axis=0).abs().max(axis=1)
    return table


# ---------------------------------------------------------------------------
# Gráficas (Plotly, para Dev A). Devuelven figuras; no llaman a fig.show().
# Streamlit:  st.plotly_chart(plot_ranking(...), use_container_width=True)
# ---------------------------------------------------------------------------

def _go():
    try:
        import plotly.graph_objects as go
    except ImportError as e:  # pragma: no cover
        raise ImportError("Falta plotly: pip install plotly") from e
    return go


def _style(fig, title: str, height: int | None = None):
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=16, color=INK)),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=FONT, color=INK_2, size=12),
        legend=dict(orientation="h", x=0, y=-0.18),
        margin=dict(l=10, r=30, t=60, b=60),
    )
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=INK_2))
    return fig


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def plot_ranking(scored: pd.DataFrame, criteria=None, id_col: str = "psi_id",
                 top_n: int = 15, label_col: str | None = None,
                 title: str = "Ranking: puntaje explicado por criterio"):
    """Barras apiladas: cuánto aporta cada criterio al puntaje de cada elemento.

    Cada criterio conserva su color según su posición en `criteria` (aunque cambien
    los pesos). Con más de 8 criterios, el resto se pliega en "Otros".
    """
    go = _go()
    crit = _resolve(criteria)
    head = scored.head(top_n).iloc[::-1]
    names = [f"#{int(r)}  {x}" for r, x in zip(head["rank"], head[label_col or id_col])]
    folded = len(crit) > len(CATEGORICAL)
    shown = crit[:7] if folded else crit
    fig = go.Figure()
    for k, c in enumerate(shown):
        fig.add_trace(go.Bar(
            orientation="h", y=names, x=head[f"contrib__{c.column}"], name=c.name,
            marker=dict(color=CATEGORICAL[k], line=dict(color=SURFACE, width=2)),
            customdata=pd.to_numeric(head[c.column], errors="coerce").round(3),
            hovertemplate="<b>%{y}</b><br>" + c.name + ": %{x:.1f} pts<br>valor: %{customdata}<extra></extra>",
        ))
    if folded:
        rest = sum(head[f"contrib__{c.column}"] for c in crit[7:])
        fig.add_trace(go.Bar(
            orientation="h", y=names, x=rest, name="Otros",
            marker=dict(color=MUTED, line=dict(color=SURFACE, width=2)),
            hovertemplate="<b>%{y}</b><br>Otros: %{x:.1f} pts<extra></extra>",
        ))
    for nm, sc in zip(names, head["score"]):
        fig.add_annotation(x=sc, y=nm, text=f"{sc:.1f}", showarrow=False,
                           xanchor="left", xshift=4, font=dict(color=INK_2, size=11))
    fig.update_layout(barmode="stack", bargap=0.35)
    fig.update_xaxes(title_text="Puntaje (0–100)", range=[0, 105])
    return _style(fig, title, height=max(320, 30 * len(head) + 150))


def plot_comparison(scored: pd.DataFrame, ids: Sequence, criteria=None,
                    id_col: str = "psi_id", title: str = "Comparación por criterio (0–1)"):
    """Radar de criterios normalizados para 2–3 elementos.

    Máximo 3: es el tope de colores que se distinguen con seguridad entre sí
    (también para daltonismo). Para más, usa `compare_items` (tabla).
    """
    go = _go()
    ids = list(ids)
    if not 2 <= len(ids) <= 3:
        raise ValueError("Compara 2 o 3 elementos.")
    crit = _resolve(criteria)
    sub = _pick(scored, id_col, ids)
    labels = [c.name for c in crit]
    fig = go.Figure()
    for k, i in enumerate(ids):
        r = [float(sub.loc[i, f"norm__{c.column}"]) for c in crit]
        raw = [pd.to_numeric(sub.loc[i, c.column], errors="coerce") for c in crit]
        fig.add_trace(go.Scatterpolar(
            r=r + r[:1], theta=labels + labels[:1], name=str(i), mode="lines+markers",
            fill="toself", fillcolor=_rgba(CATEGORICAL[k], 0.12),
            line=dict(color=CATEGORICAL[k], width=2), marker=dict(size=8, color=CATEGORICAL[k]),
            customdata=[round(float(v), 3) if pd.notna(v) else None for v in raw + raw[:1]],
            hovertemplate="<b>" + str(i) + "</b><br>%{theta}: %{r:.2f}<br>valor: %{customdata}<extra></extra>",
        ))
    fig.update_layout(polar=dict(
        bgcolor=SURFACE,
        radialaxis=dict(range=[0, 1], gridcolor=GRID, tickfont=dict(color=MUTED)),
        angularaxis=dict(gridcolor=GRID, tickfont=dict(color=INK_2)),
    ))
    return _style(fig, title, height=460)


def plot_condition_ranges(master: pd.DataFrame, ids: Sequence, id_col: str = "psi_id",
                          o2_col: str = "o2_percent", pressure_col: str = "pressure_kpa",
                          references: Mapping[str, Mapping[str, float]] | None = None,
                          title: str = "Condiciones exploradas por experimento"):
    """Segunda gráfica de la comparación: dónde midió cada elemento (O2 y presión).

    Cada punto es un ensayo; el segmento va del mínimo al máximo. Las líneas
    punteadas marcan las condiciones de referencia (Luna/Marte, ISS).
    """
    go = _go()
    from plotly.subplots import make_subplots
    ids = list(ids)
    if not 2 <= len(ids) <= 3:
        raise ValueError("Compara 2 o 3 elementos.")
    refs = DEFAULT_REFERENCES if references is None else references
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.06,
                        subplot_titles=("Oxígeno (%)", "Presión (kPa)"))
    for k, i in enumerate(ids):
        sub = master[master[id_col] == i]
        for j, (col, unit) in enumerate(((o2_col, "%"), (pressure_col, "kPa")), start=1):
            vals = pd.to_numeric(sub[col], errors="coerce").dropna()
            if vals.empty:
                continue
            fig.add_trace(go.Scatter(x=[vals.min(), vals.max()], y=[str(i)] * 2, mode="lines",
                                     line=dict(color=CATEGORICAL[k], width=2),
                                     showlegend=False, hoverinfo="skip"), row=1, col=j)
            fig.add_trace(go.Scatter(
                x=vals, y=[str(i)] * len(vals), mode="markers", name=str(i), legendgroup=str(i),
                showlegend=(j == 1),
                marker=dict(color=CATEGORICAL[k], size=9, line=dict(color=SURFACE, width=2)),
                hovertemplate="<b>" + str(i) + "</b><br>%{x:.3g} " + unit + "<extra></extra>",
            ), row=1, col=j)
    for name, ref in refs.items():
        for j, key in ((1, "o2_percent"), (2, "pressure_kpa")):
            fig.add_vline(x=ref[key], line=dict(color=MUTED, width=1, dash="dot"), row=1, col=j,
                          annotation_text=name.split(" ")[0], annotation_position="top",
                          annotation_font=dict(size=10, color=MUTED))
    return _style(fig, title, height=300 + 40 * len(ids))