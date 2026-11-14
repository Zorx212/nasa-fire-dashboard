"""Capa de datos de la app. Todo lo que lee archivos o importa modulos de
otros vive aqui, para que la app nunca se rompa si un modulo aun no existe."""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MASTER = ROOT / "data" / "processed" / "master_table.csv"
MASTER_MOCK = ROOT / "data" / "mock" / "master_table_mock.csv"
INSIGHTS = ROOT / "data" / "processed" / "insights.json"
INSIGHTS_MOCK = ROOT / "data" / "mock" / "insights_mock.json"

NUMERIC = ["o2_percent", "pressure_kpa", "flow_velocity", "gravity_level", "flame_spread_rate"]

DEFAULT_WEIGHTS = {
    "relevancia": 0.35,
    "riesgo": 0.30,
    "evidencia": 0.20,
    "cobertura": 0.15,
}


@st.cache_data
def load_master():
    """Devuelve (DataFrame, usando_mock). Los vacios quedan como NaN."""
    using_mock = not MASTER.exists()
    df = pd.read_csv(MASTER_MOCK if using_mock else MASTER)
    for col in NUMERIC:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df, using_mock


@st.cache_data
def load_insights():
    """Devuelve (lista de insights, usando_mock)."""
    using_mock = not INSIGHTS.exists()
    path = INSIGHTS_MOCK if using_mock else INSIGHTS
    with open(path, encoding="utf-8") as f:
        return json.load(f), using_mock


def _placeholder_rank(df, weights):
    """Puntaje de relleno hasta que exista src/ranking.py (Python 2)."""
    out = df.copy()
    o2 = out["o2_percent"].fillna(21)
    out["score_relevancia"] = (1 - (o2 - 21).abs() / 30).clip(0, 1)
    spread = out["flame_spread_rate"]
    out["score_riesgo"] = (spread / spread.max()).fillna(0) if spread.notna().any() else 0.0
    n = out.groupby("psi_id")["experiment_id"].transform("count")
    out["score_evidencia"] = (n / n.max()).fillna(0)
    out["score_cobertura"] = 0.5
    out["score_total"] = sum(
        weights[k] * out[f"score_{k}"] for k in weights
    ) / max(sum(weights.values()), 1e-9)
    return out.sort_values("score_total", ascending=False)


def rank(df, weights):
    """Usa src.ranking.rank si existe; si no, el puntaje de relleno.
    Contrato esperado: rank(df, weights) -> df con columnas score_* y score_total."""
    try:
        from src import ranking  # type: ignore

        return ranking.rank(df, weights)
    except Exception:
        return _placeholder_rank(df, weights)


def coverage_grid(df):
    """Usa src.coverage.coverage_grid si existe; si no, una tabla de conteos."""
    try:
        from src import coverage  # type: ignore

        return coverage.coverage_grid(df)
    except Exception:
        d = df.dropna(subset=["o2_percent", "pressure_kpa"]).copy()
        o2_bins = pd.cut(d["o2_percent"], [0, 21, 25, 30, 40, 100])
        p_bins = pd.cut(d["pressure_kpa"], [0, 35, 55, 75, 101.4, 200])
        grid = pd.crosstab(p_bins, o2_bins)  # keeps empty bins (the gaps)
        grid.index = grid.index.astype(str)
        grid.columns = grid.columns.astype(str)
        return grid


def mock_banner(using_mock):
    if using_mock:
        st.warning("Mostrando DATOS DE EJEMPLO. Aun no existe el archivo real en data/processed/.")


def citation(claim):
    page = f" · p. {claim['page']}" if claim.get("page") is not None else ""
    doi = claim.get("doi", "")
    link = f"[{doi}](https://doi.org/{doi})" if doi else "sin DOI"
    return f"`{claim.get('psi_id', '?')}` · {link}{page}"
