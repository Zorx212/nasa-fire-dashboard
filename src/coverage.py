"""coverage.py — Cobertura de condiciones y vacíos en la tabla maestra.

Space Challenge · rol Python 2 (ranking y análisis).

Responde a: "¿qué condiciones cubren los datos y cuáles no?"
(p. ej. «no hay experimentos a esta presión»).

CONTRATO con Dev A (firma exacta):

    coverage_grid(df) -> tabla de conteos
        filas    = rangos de presión (texto)
        columnas = rangos de oxígeno (texto)
        celda 0  = vacío de cobertura

Cómo funciona
-------------
1. Los ensayos se agrupan en rangos de oxígeno y presión (`DEFAULT_BINS`, editables).
2. Se arma la rejilla completa de combinaciones (O2 × presión). Cada celda cuenta
   ensayos; las celdas con 0 son los vacíos.
3. Se compara contra las condiciones de referencia de misión (Luna/Marte, ISS).

Uso rápido
----------
    from src.coverage import (coverage_grid, condition_coverage,
                              plot_coverage_heatmap, plot_gap_levels)

    grid = coverage_grid(master)                # contrato con Dev A
    plot_coverage_heatmap(grid)                 # figura Plotly

    cov = condition_coverage(master)            # master = tabla maestra
    cov["summary"]       # % de celdas cubiertas, nº de vacíos
    cov["gaps"]          # tabla de combinaciones sin datos
    cov["references"]    # ¿hay datos cerca de Luna/Marte? ¿y de la ISS?

Valores faltantes: un ensayo sin dato de O2 o presión no se asigna a ninguna celda
(nunca se cuenta como 0). Se informa en `summary["n_registros_sin_condicion"]`.

Importar como `src.coverage` (no `import coverage` suelto: choca con el paquete
`coverage` de pytest-cov).
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd

try:  # como paquete (src.coverage) o suelto
    from .ranking import (CATEGORICAL, DEFAULT_REFERENCES, FONT, GRID, INK, INK_2,
                          MUTED, SURFACE, _go, _style)
except ImportError:  # pragma: no cover
    from ranking import (CATEGORICAL, DEFAULT_REFERENCES, FONT, GRID, INK, INK_2,  # type: ignore
                         MUTED, SURFACE, _go, _style)

__all__ = [
    "DEFAULT_BINS", "bin_conditions", "coverage_table", "coverage_matrix",
    "find_gaps", "coverage_summary", "coverage_by_level", "missing_report",
    "reference_coverage", "condition_coverage", "plot_coverage_heatmap",
    "plot_gap_levels", "coverage_grid",
]

# Bordes de los rangos (intervalos [a, b)). Editables. 56.5 kPa (≈8.2 psia) cae en
# "50–70" y 101.3 kPa en "90–110"; 21 % de O2 abre el rango "21–30".
DEFAULT_BINS: dict[str, list[float]] = {
    "o2_percent": [0, 15, 21, 30, 40, np.inf],
    "pressure_kpa": [0, 30, 50, 70, 90, 110, np.inf],
}


# ---------------------------------------------------------------------------
# Rejilla de cobertura
# ---------------------------------------------------------------------------

def _bin_labels(edges: Sequence[float]) -> list[str]:
    return [f"≥{lo:g}" if np.isinf(hi) else f"{lo:g}–{hi:g}" for lo, hi in zip(edges[:-1], edges[1:])]


def bin_conditions(df: pd.DataFrame, bins: Mapping[str, Sequence[float]] | None = None,
                   suffix: str = "_bin") -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Agrega columnas `<col>_bin` con el rango de cada ensayo.

    Devuelve (df con rangos, niveles esperados por columna). Los niveles esperados
    incluyen los rangos sin datos: así aparecen como vacíos en vez de desaparecer.
    """
    bins = DEFAULT_BINS if bins is None else bins
    out = df.copy()
    levels: dict[str, list[str]] = {}
    for col, edges in bins.items():
        if col not in df.columns:
            continue
        labels = _bin_labels(edges)
        x = pd.to_numeric(df[col], errors="coerce")
        out[f"{col}{suffix}"] = pd.cut(x, bins=list(edges), labels=labels, right=False).astype(object)
        levels[f"{col}{suffix}"] = labels
    return out, levels


def _levels(df: pd.DataFrame, dims: Sequence[str], expected: Mapping[str, Sequence] | None) -> dict[str, list]:
    expected = expected or {}
    out: dict[str, list] = {}
    for d in dims:
        if d not in df.columns:
            raise KeyError(f"No existe la columna '{d}'.")
        if d in expected:
            out[d] = list(expected[d])
        else:
            vals = pd.Series(df[d].dropna().unique()).tolist()
            try:
                vals = sorted(vals)
            except TypeError:
                vals = sorted(vals, key=str)
            out[d] = vals
    return out


def coverage_table(df: pd.DataFrame, dims: Sequence[str], expected: Mapping[str, Sequence] | None = None,
                   id_col: str | None = None) -> pd.DataFrame:
    """Todas las combinaciones posibles de `dims` con su conteo `n` (0 = vacío).

    Cuenta ensayos, o elementos distintos de `id_col` (p. ej. investigaciones PSI).
    Filas con NaN en alguna dimensión no se asignan a ninguna celda.
    """
    dims = list(dims)
    levels = _levels(df, dims, expected)
    if len(dims) == 1:
        full = pd.Index(levels[dims[0]], name=dims[0])
    else:
        full = pd.MultiIndex.from_product([levels[d] for d in dims], names=dims)
    sub = df.dropna(subset=dims)
    if sub.empty:
        counts = pd.Series(0, index=full)
    else:
        grp = sub.groupby(dims, observed=True)
        counts = (grp[id_col].nunique() if id_col else grp.size()).reindex(full, fill_value=0)
    tbl = counts.rename("n").reset_index()
    tbl["n"] = tbl["n"].astype(int)
    return tbl


def coverage_matrix(df: pd.DataFrame, row_dim: str, col_dim: str, id_col: str | None = None,
                    expected: Mapping[str, Sequence] | None = None) -> pd.DataFrame:
    """Matriz de conteos (filas × columnas) lista para un mapa de calor."""
    tbl = coverage_table(df, [row_dim, col_dim], expected, id_col)
    rows = list(dict.fromkeys(tbl[row_dim]))
    cols = list(dict.fromkeys(tbl[col_dim]))
    return pd.DataFrame(tbl["n"].to_numpy().reshape(len(rows), len(cols)),
                        index=pd.Index(rows, name=row_dim), columns=pd.Index(cols, name=col_dim))


def coverage_grid(df: pd.DataFrame) -> pd.DataFrame:
    """Contrato con Dev A: conteo de ensayos por rango de presión (filas) y de oxígeno (columnas).

    Etiquetas en texto ("50–70", "≥110"); una celda en 0 es un vacío de cobertura.
    Los ensayos sin O2 o sin presión no caen en ninguna celda (ver
    `condition_coverage(df)["summary"]["n_registros_sin_condicion"]`).
    Los rangos se cambian en `DEFAULT_BINS`.
    """
    missing = [c for c in ("o2_percent", "pressure_kpa") if c not in df.columns]
    if missing:
        raise KeyError(f"Faltan columnas en df: {missing}")
    binned, levels = bin_conditions(df)
    grid = coverage_matrix(binned, "pressure_kpa_bin", "o2_percent_bin", expected=levels)
    grid.index.name = "Presión (kPa)"
    grid.columns.name = "Oxígeno (%)"
    return grid


def find_gaps(df: pd.DataFrame, dims: Sequence[str], expected: Mapping[str, Sequence] | None = None,
              id_col: str | None = None, min_count: int = 1) -> pd.DataFrame:
    """Combinaciones con menos de `min_count` ensayos (por defecto, sin ninguno)."""
    tbl = coverage_table(df, dims, expected, id_col)
    return tbl[tbl["n"] < min_count].reset_index(drop=True)


def coverage_summary(df: pd.DataFrame, dims: Sequence[str], expected: Mapping[str, Sequence] | None = None,
                     id_col: str | None = None, min_count: int = 1) -> dict:
    """Resumen: combinaciones totales, cubiertas, vacíos y % de cobertura."""
    dims = list(dims)
    tbl = coverage_table(df, dims, expected, id_col)
    covered = tbl["n"] >= min_count
    return {
        "dimensiones": dims,
        "n_registros": int(len(df)),
        "n_registros_sin_condicion": int(df[dims].isna().any(axis=1).sum()),
        "n_combinaciones": int(len(tbl)),
        "n_cubiertas": int(covered.sum()),
        "n_vacios": int((~covered).sum()),
        "pct_cobertura": round(float(100 * covered.mean()), 1) if len(tbl) else float("nan"),
    }


def coverage_by_level(df: pd.DataFrame, dims: Sequence[str], expected: Mapping[str, Sequence] | None = None,
                      id_col: str | None = None, min_count: int = 1) -> pd.DataFrame:
    """Por cada nivel de cada dimensión: % de combinaciones (con las otras
    dimensiones) que tienen datos. Un nivel con 0 % es un rango sin experimentos."""
    dims = list(dims)
    tbl = coverage_table(df, dims, expected, id_col)
    tbl["_cub"] = tbl["n"] >= min_count
    parts = []
    for d in dims:
        g = tbl.groupby(d, sort=False, observed=True).agg(
            n_registros=("n", "sum"), n_combinaciones=("_cub", "size"), n_cubiertas=("_cub", "sum"))
        g["pct_cobertura"] = (100 * g["n_cubiertas"] / g["n_combinaciones"]).round(1)
        g = g.reset_index().rename(columns={d: "nivel"})
        g.insert(0, "dimension", d)
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def missing_report(df: pd.DataFrame, columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Vacíos de datos: cuántos valores faltan por columna."""
    cols = list(columns) if columns is not None else list(df.columns)
    rep = pd.DataFrame({"columna": cols, "n_faltantes": [int(df[c].isna().sum()) for c in cols]})
    rep["pct_faltantes"] = (100 * rep["n_faltantes"] / max(len(df), 1)).round(1)
    return rep.sort_values(["pct_faltantes", "columna"], ascending=[False, True]).reset_index(drop=True)


def reference_coverage(master: pd.DataFrame, references: Mapping[str, Mapping[str, float]] | None = None,
                       tol_o2: float = 5.0, tol_p: float = 10.0, o2_col: str = "o2_percent",
                       pressure_col: str = "pressure_kpa", id_col: str | None = "psi_id") -> pd.DataFrame:
    """¿Hay datos cerca de las condiciones de misión?

    Cuenta ensayos a ±`tol_o2` puntos de O2 y ±`tol_p` kPa de cada referencia.
    """
    refs = DEFAULT_REFERENCES if references is None else references
    o2 = pd.to_numeric(master[o2_col], errors="coerce")
    p = pd.to_numeric(master[pressure_col], errors="coerce")
    rows = []
    for name, ref in refs.items():
        near = ((o2 - ref["o2_percent"]).abs() <= tol_o2) & ((p - ref["pressure_kpa"]).abs() <= tol_p)
        n_inv = int(master.loc[near, id_col].nunique()) if id_col and id_col in master.columns else None
        rows.append({
            "referencia": name, "o2_percent": ref["o2_percent"], "pressure_kpa": ref["pressure_kpa"],
            "n_ensayos": int(near.sum()), "n_investigaciones": n_inv,
            "estado": "cubierta" if near.any() else "VACÍO: sin experimentos cerca de estas condiciones",
        })
    return pd.DataFrame(rows)


def condition_coverage(master: pd.DataFrame, bins: Mapping[str, Sequence[float]] | None = None,
                       id_col: str | None = None, extra_dims: Sequence[str] = (),
                       min_count: int = 1, references: Mapping[str, Mapping[str, float]] | None = None,
                       tol_o2: float = 5.0, tol_p: float = 10.0,
                       investigation_col: str = "psi_id") -> dict:
    """Todo en un paso para la pantalla «Cobertura y vacíos».

    `id_col=None` cuenta ensayos; `id_col="psi_id"` cuenta investigaciones distintas.
    `extra_dims` suma columnas categóricas (p. ej. "material_type") a la rejilla.
    Devuelve: binned, dims, levels, matrix (O2 × presión), table, gaps, summary,
    by_level, references, missing.
    """
    binned, levels = bin_conditions(master, bins)
    dims = list(levels)
    if not dims:
        raise KeyError("Ninguna columna de `bins` está en la tabla (¿o2_percent, pressure_kpa?).")
    dims += list(extra_dims)
    exp = dict(levels)
    out = {
        "binned": binned, "dims": dims, "levels": levels,
        "table": coverage_table(binned, dims, exp, id_col),
        "gaps": find_gaps(binned, dims, exp, id_col, min_count),
        "summary": coverage_summary(binned, dims, exp, id_col, min_count),
        "by_level": coverage_by_level(binned, dims, exp, id_col, min_count),
        "missing": missing_report(master, [c for c in bins_cols(bins, master)]),
        "matrix": coverage_matrix(binned, dims[0], dims[1], id_col, exp) if len(dims) >= 2 else None,
    }
    if {"o2_percent", "pressure_kpa"} <= set(master.columns):
        out["references"] = reference_coverage(
            master, references, tol_o2, tol_p,
            id_col=investigation_col if investigation_col in master.columns else None)
    return out


def bins_cols(bins: Mapping[str, Sequence[float]] | None, master: pd.DataFrame) -> list[str]:
    return [c for c in (DEFAULT_BINS if bins is None else bins) if c in master.columns]


# ---------------------------------------------------------------------------
# Gráficas (Plotly, para Dev A)
# ---------------------------------------------------------------------------

# Azul secuencial (pasos 100 → 400 → 700 de la paleta): claro = pocos ensayos.
_SEQUENTIAL = [[0.0, "#cde2fb"], [0.5, "#3987e5"], [1.0, "#0d366b"]]


def plot_coverage_heatmap(matrix: pd.DataFrame, title: str | None = None, show_values: bool = True,
                          count_label: str = "ensayos"):
    """Mapa de calor de conteos (acepta la salida de `coverage_grid`). Celdas vacías = en blanco con un 0 gris."""
    go = _go()
    z = matrix.to_numpy(dtype=float)
    z_masked = np.where(z > 0, z, np.nan)
    text = np.where(z > 0, z.astype(int).astype(str), "0")
    x = [str(v) for v in matrix.columns]
    y = [str(v) for v in matrix.index]
    fig = go.Figure(go.Heatmap(
        z=z_masked, x=x, y=y, text=text, colorscale=_SEQUENTIAL, zmin=0, xgap=2, ygap=2,
        hoverongaps=True, colorbar=dict(title=count_label, thickness=12),
        hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>%{text} " + count_label + "<extra></extra>",
    ))
    if show_values and z.size <= 400:
        zmax = np.nanmax(z) if z.size and np.nanmax(z) > 0 else 1.0
        for i, yi in enumerate(y):
            for j, xj in enumerate(x):
                v = z[i, j]
                color = MUTED if v == 0 else ("#ffffff" if v / zmax > 0.5 else INK)
                fig.add_annotation(x=xj, y=yi, text=text[i, j], showarrow=False,
                                   font=dict(color=color, size=11))
    fig.update_xaxes(title_text=str(matrix.columns.name or ""), type="category")
    fig.update_yaxes(title_text=str(matrix.index.name or ""), type="category", autorange="reversed")
    default = "Cobertura de condiciones: las celdas en blanco son vacíos (0 ensayos)"
    return _style(fig, title or default, height=max(320, 56 * len(y) + 160))


def plot_gap_levels(by_level: pd.DataFrame, title: str = "Cobertura por rango (% de combinaciones con datos)"):
    """Barras por nivel: los rangos con menos cobertura quedan arriba."""
    go = _go()
    d = by_level.sort_values(["pct_cobertura", "dimension", "nivel"], ascending=[False, True, True])
    labels = [f"{a}: {b}" for a, b in zip(d["dimension"], d["nivel"])]
    fig = go.Figure(go.Bar(
        orientation="h", y=labels, x=d["pct_cobertura"],
        marker=dict(color=CATEGORICAL[0], line=dict(color=SURFACE, width=2)),
        customdata=np.column_stack([d["n_cubiertas"], d["n_combinaciones"]]),
        hovertemplate="<b>%{y}</b><br>%{x:.1f} % cubierto (%{customdata[0]} de %{customdata[1]} combinaciones)<extra></extra>",
    ))
    fig.update_layout(bargap=0.4, showlegend=False)
    fig.update_xaxes(title_text="% con datos", range=[0, 100])
    return _style(fig, title, height=max(300, 30 * len(d) + 140))