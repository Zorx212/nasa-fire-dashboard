"""Pruebas del contrato Python 2 (rank, coverage_grid) y de humo para el resto."""
import numpy as np
import pandas as pd
import pytest

from src.coverage import (condition_coverage, coverage_grid, plot_coverage_heatmap,
                          plot_gap_levels)
from src.ranking import (RANK_WEIGHT_KEYS, build_features, compare_items, explain_item,
                         plot_ranking, rank, rank_contributions, rank_master, weight_sensitivity)

W = {"relevancia": 0.35, "riesgo": 0.2, "evidencia": 0.25, "cobertura": 0.2}
SCORES = [f"score_{k}" for k in RANK_WEIGHT_KEYS] + ["score_total"]
COLUMNS = ["experiment_id", "psi_id", "doi", "license", "title", "material_or_fuel",
           "material_type", "o2_percent", "pressure_kpa", "flow_velocity", "gravity_level",
           "flame_outcome", "flame_spread_rate", "spread_rate_unit", "source_file",
           "source_page", "notes"]


def make_mock():
    """Tabla con el formato del contrato de Python 1 (17 columnas) y NaN donde falta."""
    rows = [
        # psi, o2, kPa, flujo, resultado, tasa, página
        ("PSI-1", 34.0, 56.5, 0.0, "propagó", 1.2, 3),
        ("PSI-1", 21.0, 101.3, 5.0, "se extinguió", np.nan, 4),
        ("PSI-1", 25.0, 70.0, 10.0, "no propagó", 0.0, 4),
        ("PSI-1", 40.0, 30.0, 2.0, "otro", 0.5, 5),
        ("PSI-2", 5.0, 10.0, np.nan, "propagó", 3.0, 7),
        ("PSI-2", np.nan, 70.3, 10.0, "se extinguió", np.nan, np.nan),
        ("PSI-3", 26.5, np.nan, 2.0, np.nan, np.nan, np.nan),
        (np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan),
    ]
    recs = []
    for i, (psi, o2, p, flow, outcome, spread, page) in enumerate(rows):
        r = dict.fromkeys(COLUMNS, np.nan)
        r.update(experiment_id=f"E{i}", psi_id=psi, doi="10.0/x" if pd.notna(psi) and psi != "PSI-3" else np.nan,
                 o2_percent=o2, pressure_kpa=p, flow_velocity=flow, flame_outcome=outcome,
                 flame_spread_rate=spread, source_page=page, material_type="sólido")
        recs.append(r)
    return pd.DataFrame(recs, columns=COLUMNS)


# ---------------------------- contrato rank ----------------------------

def test_rank_adds_only_the_five_score_columns_and_keeps_rows():
    df = make_mock()
    before = df.copy()
    out = rank(df, W)
    pd.testing.assert_frame_equal(df, before)                 # no muta la entrada
    assert list(out.columns) == list(df.columns) + SCORES
    assert out.index.equals(df.index) and len(out) == len(df)
    assert out["experiment_id"].tolist() == df["experiment_id"].tolist()   # mismo orden


def test_scores_are_between_0_and_1_and_never_nan():
    out = rank(make_mock(), W)
    assert out[SCORES].notna().all().all()
    assert ((out[SCORES] >= 0) & (out[SCORES] <= 1)).all().all()


def test_index_is_preserved_when_df_is_filtered():
    df = make_mock().iloc[[5, 1, 3]]
    out = rank(df, W)
    assert out.index.tolist() == [5, 1, 3]


def test_weights_are_normalized():
    a = rank(make_mock(), W)["score_total"]
    b = rank(make_mock(), {k: v * 10 for k, v in W.items()})["score_total"]
    pd.testing.assert_series_equal(a, b)


def test_total_is_weighted_sum_of_components():
    out = rank(make_mock(), W)
    parts = rank_contributions(out, W)
    pd.testing.assert_series_equal(parts.sum(axis=1), out["score_total"], check_names=False)


def test_relevancia_and_missing_values():
    out = rank(make_mock(), W)
    assert out.loc[0, "score_relevancia"] == pytest.approx(1.0)    # 34 % / 56.5 kPa
    assert out.loc[4, "score_relevancia"] == 0.0                   # 5 % / 10 kPa: lejos
    assert out.loc[5, "score_relevancia"] == 0.0                   # falta O2 -> no suma
    assert out.loc[7, "score_relevancia"] == 0.0                   # fila vacía


def test_riesgo_outcomes():
    out = rank(make_mock(), W)["score_riesgo"]
    assert out[0] == 1.0          # propagó
    assert out[1] == 0.0          # se extinguió
    assert out[2] == 0.0          # "no propagó" NO cuenta como propagación
    assert out[3] == 0.5          # otro
    assert out[6] == 0.0          # sin dato -> no suma


def test_cobertura_prefers_investigation_with_more_conditions():
    out = rank(make_mock(), W)["score_cobertura"]
    assert out[0] == 1.0 and out[0] == out[3]    # PSI-1 es la que más condiciones explora
    assert out[4] < out[0]
    assert out[7] == 0.0


def test_all_missing_conditions_does_not_break():
    df = make_mock()
    df[["o2_percent", "pressure_kpa", "flow_velocity"]] = np.nan
    out = rank(df, W)
    assert out[SCORES].notna().all().all() and (out["score_cobertura"] == 0).all()


@pytest.mark.parametrize("bad", [
    {"relevancia": 1, "riesgo": 1, "evidencia": 1},
    {**W, "extra": 1},
    {**W, "riesgo": -1},
    {**W, "riesgo": float("nan")},
    {k: 0 for k in W},
])
def test_invalid_weights_raise(bad):
    with pytest.raises(ValueError):
        rank(make_mock(), bad)


def test_missing_required_column_raises():
    with pytest.raises(KeyError):
        rank(make_mock().drop(columns=["pressure_kpa"]), W)


# ---------------------------- contrato coverage_grid ----------------------------

def test_coverage_grid_shape_labels_and_orientation():
    grid = coverage_grid(make_mock())
    assert grid.shape == (6, 5)                                  # 6 rangos de presión × 5 de O2
    assert all(isinstance(x, str) for x in list(grid.index) + list(grid.columns))
    assert "Presión" in grid.index.name and "Oxígeno" in grid.columns.name
    assert grid.loc["50–70", "30–40"] == 1                       # 34 % y 56.5 kPa
    assert grid.iloc[-1].sum() == 0                              # nada a ≥110 kPa


def test_coverage_grid_counts_only_located_rows_and_has_gaps():
    df = make_mock()
    grid = coverage_grid(df)
    located = (df["o2_percent"].notna() & df["pressure_kpa"].notna()).sum()
    assert grid.to_numpy().sum() == located == 5
    assert (grid == 0).any().any()
    assert np.issubdtype(grid.to_numpy().dtype, np.integer)


def test_coverage_grid_empty_and_missing_columns():
    assert coverage_grid(make_mock().iloc[0:0]).to_numpy().sum() == 0
    with pytest.raises(KeyError):
        coverage_grid(make_mock().drop(columns=["o2_percent"]))


# ---------------------------- tus funciones (humo tras los cambios) ----------------------------

def test_rank_master_and_helpers_still_work():
    master = make_mock()
    scored, crit = rank_master(master)
    assert scored["rank"].min() == 1 and {"PSI-1", "PSI-2", "PSI-3"} <= set(scored["psi_id"])
    assert "puesto" in explain_item(scored, "PSI-1", crit)
    assert compare_items(scored, ["PSI-1", "PSI-2"], crit).shape[1] == 3
    assert len(weight_sensitivity(build_features(master), crit)) >= 1
    filtered, _ = rank_master(master, filters={"o2_range": (20, 40)})
    assert set(filtered["psi_id"]) <= {"PSI-1", "PSI-3"}


def test_condition_coverage_summary():
    cov = condition_coverage(make_mock())
    assert cov["summary"]["n_registros_sin_condicion"] == 3
    assert cov["summary"]["n_vacios"] > 0
    assert cov["references"]["n_ensayos"].tolist()[0] >= 1


def test_plots_build_if_plotly_is_installed():
    pytest.importorskip("plotly")
    master = make_mock()
    scored, crit = rank_master(master)
    plot_ranking(scored, crit)
    plot_coverage_heatmap(coverage_grid(master))
    plot_gap_levels(condition_coverage(master)["by_level"])