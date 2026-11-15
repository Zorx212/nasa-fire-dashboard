"""Pruebas de escenarios, gravedad, relevancia por escenario y revisión de la tabla maestra."""
import inspect

import numpy as np
import pandas as pd
import pytest

from src.ranking import build_features, rank
from src.scenarios import (EXPECTED_COLUMNS, GRAVITY_CATEGORIES, O2_SCALE, P_SCALE, SCENARIOS, Scenario,
                           check_master, classify_gravity, gravity_counts, rank_scenario,
                           scenario_cells, scenario_counts, scenario_mask, scenario_relevance)

W = {"relevancia": 0.35, "riesgo": 0.2, "evidencia": 0.25, "cobertura": 0.2}


def make_df(with_partial_lunar=False):
    rows = [  # psi, o2, kPa, gravedad
        ("PSI-1", 34.0, 56.5, "microgravedad"),     # atmósfera lunar, micro
        ("PSI-1", 30.0, 60.0, 1e-4),                # atmósfera lunar, micro (numérico)
        ("PSI-1", 21.0, 101.3, 1.0),                # ISS / Tierra, normal
        ("PSI-2", 100.0, 30.0, "microgravity"),     # traje
        ("PSI-2", np.nan, 60.0, np.nan),            # sin O2, sin gravedad
        ("PSI-3", 25.0, 70.0, "otra cosa"),         # sin clasificar
    ]
    if with_partial_lunar:
        rows.append(("PSI-3", 34.0, 56.5, 0.166))   # atmósfera lunar + gravedad lunar
    df = pd.DataFrame(rows, columns=["psi_id", "o2_percent", "pressure_kpa", "gravity_level"])
    df.insert(0, "experiment_id", [f"E{i}" for i in range(len(df))])
    for c in ("flame_outcome", "flame_spread_rate", "flow_velocity", "doi", "source_page"):
        df[c] = np.nan
    return df


# ---------------------------- gravedad ----------------------------

@pytest.mark.parametrize("value,expected", [
    (1e-5, "microgravedad"), (0.0, "microgravedad"), ("Microgravity", "microgravedad"),
    (0.166, "parcial"), (0.38, "parcial"), ("lunar", "parcial"), ("Partial gravity", "parcial"),
    (1.0, "normal"), ("1 g", "normal"), ("Tierra", "normal"), ("1.0", "normal"),
    (9.8, "sin clasificar"), (-1.0, "sin clasificar"), ("no sé", "sin clasificar"),
    (np.nan, "sin dato"), (None, "sin dato"),
])
def test_gravity_classification(value, expected):
    assert classify_gravity(pd.Series([value], dtype=object)).iloc[0] == expected


def test_gravity_counts_always_has_all_categories_and_explicit_zero():
    counts = gravity_counts(make_df())
    assert counts["categoria"].tolist() == list(GRAVITY_CATEGORIES)
    by = counts.set_index("categoria")["n_ensayos"]
    assert by["parcial"] == 0 and by["microgravedad"] == 3 and by["normal"] == 1
    assert by["sin clasificar"] == 1 and by["sin dato"] == 1
    assert by.sum() == len(make_df())


def test_gravity_counts_requires_column():
    with pytest.raises(KeyError):
        gravity_counts(make_df().drop(columns=["gravity_level"]))


# ---------------------------- escenarios ----------------------------

def test_scenarios_are_defined_once_with_source():
    assert list(SCENARIOS) == ["Base lunar", "Traje espacial", "ISS / Tierra"]
    for sc in SCENARIOS.values():
        assert sc.o2[0] <= sc.o2[1] and sc.pressure_kpa[0] <= sc.pressure_kpa[1]
        assert "supuesto del equipo" in sc.source and "ntrs.nasa.gov" in sc.source


def test_scenario_counts_flags_the_partial_gravity_gap():
    counts = scenario_counts(make_df()).set_index("escenario")
    lunar = counts.loc["Base lunar"]
    assert lunar["n_atmosfera"] == 2 and lunar["n_atmosfera_y_gravedad"] == 0
    assert lunar["estado"].startswith("VACÍO") and "parcial" in lunar["estado"]
    assert counts.loc["Traje espacial", "n_atmosfera"] == 1 and counts.loc["Traje espacial", "estado"] == "cubierto"
    assert counts.loc["ISS / Tierra", "n_atmosfera"] == 1
    assert (counts["n_sin_dato"] == 1).all()


def test_scenario_counts_covered_when_partial_gravity_exists():
    lunar = scenario_counts(make_df(with_partial_lunar=True)).set_index("escenario").loc["Base lunar"]
    assert lunar["n_atmosfera_y_gravedad"] == 1 and lunar["estado"] == "cubierto"


def test_scenario_counts_empty_atmosphere():
    df = make_df()
    df["o2_percent"] = 5.0
    assert scenario_counts(df).set_index("escenario").loc["ISS / Tierra", "estado"].startswith("VACÍO: 0 ensayos")


def test_scenario_mask_never_includes_rows_without_o2_or_pressure():
    df = make_df()
    for name in SCENARIOS:
        assert not scenario_mask(df, name).iloc[4]


def test_unknown_scenario_raises():
    with pytest.raises(KeyError):
        scenario_mask(make_df(), "Marte")


def test_scenario_cells_match_coverage_grid_labels():
    from src.coverage import coverage_grid
    grid = coverage_grid(make_df())
    for name in SCENARIOS:
        cells = scenario_cells(name)
        assert set(cells["presion"]) <= set(grid.index) and set(cells["oxigeno"]) <= set(grid.columns)
        assert cells["presion"] and cells["oxigeno"]
    lunar = scenario_cells("Base lunar")
    assert lunar["presion"] == ["50–70", "70–90"] and lunar["oxigeno"] == ["21–30", "30–40"]


# ---------------------------- relevancia por escenario ----------------------------

def test_scales_match_build_features_defaults():
    p = inspect.signature(build_features).parameters
    assert (p["o2_scale"].default, p["p_scale"].default) == (O2_SCALE, P_SCALE)


def test_scenario_relevance_inside_outside_and_missing():
    rel = scenario_relevance(make_df(), "Base lunar")
    assert rel.iloc[0] == 1.0 and rel.iloc[1] == 1.0       # dentro del rango
    assert 0 < rel.iloc[5] < 1                              # cerca
    assert rel.iloc[2] < rel.iloc[5]                        # ISS está más lejos de la base lunar
    assert rel.iloc[4] == 0.0                               # falta O2


def test_point_scenario_equals_ranking_relevance():
    df = make_df()
    point = Scenario("punto", o2=(34.0, 34.0), pressure_kpa=(56.5, 56.5), gravity=None, source="prueba")
    ref = build_features(df, level="experiment",
                         references={"x": {"o2_percent": 34.0, "pressure_kpa": 56.5}})["relevancia"].fillna(0.0)
    np.testing.assert_allclose(scenario_relevance(df, point).to_numpy(), ref.to_numpy())


def test_rank_scenario_changes_only_relevance_and_total():
    df = make_df()
    base = rank(df, W)
    lunar = rank_scenario(df, W, "Base lunar")
    assert list(lunar.columns) == list(base.columns) and lunar.index.equals(df.index)
    for c in ("score_riesgo", "score_evidencia", "score_cobertura"):
        pd.testing.assert_series_equal(lunar[c], base[c])
    assert (lunar["score_relevancia"] != base["score_relevancia"]).any()
    scores = [f"score_{k}" for k in ("relevancia", "riesgo", "evidencia", "cobertura")] + ["score_total"]
    assert lunar[scores].notna().all().all() and ((lunar[scores] >= 0) & (lunar[scores] <= 1)).all().all()
    expected = 0.35 * lunar["score_relevancia"] + 0.2 * lunar["score_riesgo"] \
        + 0.25 * lunar["score_evidencia"] + 0.2 * lunar["score_cobertura"]
    np.testing.assert_allclose(lunar["score_total"], expected)


def test_rank_scenario_validates_weights_and_scenario():
    with pytest.raises(ValueError):
        rank_scenario(make_df(), {"relevancia": 1}, "Base lunar")
    with pytest.raises(KeyError):
        rank_scenario(make_df(), W, "Marte")


# ---------------------------- revisión de la tabla ----------------------------

def clean_table():
    df = pd.DataFrame({c: [np.nan, np.nan] for c in EXPECTED_COLUMNS})
    df["experiment_id"] = ["E1", "E2"]
    df["psi_id"] = ["PSI-1", "PSI-1"]
    df["doi"] = "10.0/x"
    df["license"] = "CC0-1.0"
    df["o2_percent"] = [21.0, 34.0]
    df["pressure_kpa"] = [101.3, 56.5]
    df["gravity_level"] = [1e-4, 1e-4]
    df["flame_outcome"] = ["propagó", "se extinguió"]
    df["flame_spread_rate"] = [1.0, 2.0]
    df["spread_rate_unit"] = "mm/s"
    return df


def test_check_master_clean_table_has_no_problems():
    assert check_master(clean_table()).empty


def test_check_master_detects_typical_real_data_problems():
    df = clean_table()
    df.loc[1, "experiment_id"] = "E1"                   # repetido
    df.loc[0, "o2_percent"] = 0.0                       # 0 en vez de vacío
    df.loc[1, "o2_percent"] = 250.0                     # imposible
    df["pressure_kpa"] = df["pressure_kpa"].astype(object)
    df.loc[0, "pressure_kpa"] = "alta"                  # no numérico
    df.loc[1, "spread_rate_unit"] = "cm/s"              # unidades mezcladas
    df.loc[0, "flame_outcome"] = "quién sabe"
    df.loc[1, "gravity_level"] = 9.8
    problems = " | ".join(check_master(df)["problema"])
    for fragment in ("repetido", "probable dato faltante", "fuera de 0–100", "no son números",
                     "unidades mezcladas", "no reconocido", "no se pudo clasificar"):
        assert fragment in problems, fragment


def test_check_master_missing_column_is_an_error_and_errors_come_first():
    out = check_master(clean_table().drop(columns=["gravity_level"]))
    assert out.iloc[0]["severidad"] == "error" and out.iloc[0]["columna"] == "gravity_level"