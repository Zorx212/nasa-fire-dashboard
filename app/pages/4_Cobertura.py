from html import escape as E

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from data_loader import load_master, mock_banner

ui.setup("Cobertura")
df, using_mock = load_master()
ui.sidebar(df, using_mock)  # la cobertura evalúa todos los datos de la tabla maestra
ui.tabs(3)
mock_banner(using_mock)

nl = ui.zone_count(df, "Base Lunar / Rover")
g = pd.to_numeric(df["gravity_level"], errors="coerce") if "gravity_level" in df.columns else pd.Series(dtype=float)
n0 = int((g == 0).sum()) if not g.empty else 0
n1 = int((g == 1).sum()) if not g.empty else 0
npar = int(((g > 0) & (g < 1)).sum()) if not g.empty else 0

hero_cls = "gap-hero has-data" if npar > 0 else "gap-hero"
st.markdown(
    f'<div class="{hero_cls}">'
    f'<div class="gap-line">'
    f'<span class="gap-num">{npar}</span>'
    f'<span class="gap-unit">pruebas en gravedad parcial real (1/6 g · 3/8 g)</span>'
    f'</div>'
    f'<div class="gap-sub">{nl} pruebas dentro de Base Lunar / Rover (30–60 % O₂, hasta 70.3 kPa)</div>'
    f'</div>',
    unsafe_allow_html=True,
)

valid = df.copy()
valid["o2_num"] = pd.to_numeric(valid["o2_percent"], errors="coerce")
valid["pr_num"] = pd.to_numeric(valid["pressure_kpa"], errors="coerce")
valid = valid.dropna(subset=["o2_num", "pr_num"]).copy()

fig = go.Figure()

zone_anchors = {
    "Base Lunar / Rover": (45.0, 56.0, "center", "middle"),
    "Traje Espacial": (99.5, 22.0, "right", "middle"),
    "ISS / Tierra": (19.0, 93.5, "left", "top"),
}
for nombre, z in ui.SCEN.items():
    x0, x1 = z["o2"]
    y0, y1 = z["p"]
    nz = ui.zone_count(df, nombre)
    zx = [x0, x1, x1, x0, x0]
    zy = [y0, y0, y1, y1, y0]
    if nz == 0:
        fig.add_trace(
            go.Scatter(
                x=zx,
                y=zy,
                mode="lines",
                fill="toself",
                fillpattern=dict(
                    shape="/",
                    size=7,
                    solidity=0.25,
                    fgcolor="#B91C1C",
                    bgcolor="rgba(0,0,0,0)",
                ),
                line=dict(color="#B91C1C", width=1.6, dash="dash"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=zx,
                y=zy,
                mode="lines",
                fill="toself",
                fillcolor="rgba(100,116,139,0.09)",
                line=dict(color="#64748B", width=1.5, dash="dash"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
    ax, ay, x_anc, y_anc = zone_anchors.get(nombre, ((x0 + x1) / 2, (y0 + y1) / 2, "center", "middle"))
    lbl = f"{nombre} · {nz} pruebas" if nz > 0 else f"{nombre} · sin pruebas"
    fig.add_annotation(
        x=ax,
        y=ay,
        xanchor=x_anc,
        yanchor=y_anc,
        text=lbl,
        showarrow=False,
        font=dict(size=12, color="#B91C1C" if nz == 0 else "#0F172A"),
        bgcolor="rgba(255,255,255,0.88)",
        borderpad=3,
    )

palette = {
    "sólido": ("#E84C22", "circle"),
    "solido": ("#E84C22", "circle"),
    "solid": ("#E84C22", "circle"),
    "gas": ("#1D4ED8", "diamond"),
    "líquido": ("#0F766E", "square"),
    "liquido": ("#0F766E", "square"),
    "liquid": ("#0F766E", "square"),
}
mat_types = list(dict.fromkeys(valid["material_type"].dropna().astype(str)))
for t in mat_types:
    d = valid[valid["material_type"].astype(str) == t]
    if d.empty:
        continue
    col, sym = palette.get(t.lower(), ("#0F766E", "square"))
    hover_texts = [
        f"<b>{E(ui.clean_str(row.get('experiment_id')))} · {E(ui.clean_str(row.get('psi_id')))}</b><br>"
        f"O₂: {row['o2_num']:.1f} % · Presión: {row['pr_num']:.1f} kPa<br>"
        f"{E(ui.clean_str(row.get('material_or_fuel')))} · {E(ui.outcome_label(row.get('flame_outcome')))}"
        for _, row in d.iterrows()
    ]
    fig.add_trace(
        go.Scatter(
            x=d["o2_num"],
            y=d["pr_num"],
            mode="markers",
            name=ui.mat_label(t),
            marker=dict(color=col, size=7, symbol=sym),
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
        )
    )

y_top = min(135.0, max(115.0, float(valid["pr_num"].max()) * 1.08)) if not valid.empty else 115.0
fig = ui.style_fig(fig, 420)
fig.update_layout(
    title=None,
    xaxis_title="Oxígeno (%)",
    yaxis_title="Presión (kPa)",
    xaxis=dict(range=[-2, 103]),
    yaxis=dict(range=[-4, y_top]),
    legend=dict(
        x=0.99,
        y=0.98,
        xanchor="right",
        yanchor="top",
        bgcolor="rgba(255,255,255,0.8)",
        title_text="",
    ),
    margin=dict(l=10, r=10, t=12, b=36),
)

with st.container(key="cov_map_ficha"):
    st.markdown('<span class="tag">Mapa de cobertura</span>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:13px;font-weight:500;color:#0F172A;margin-bottom:4px">Oxígeno (%) frente a presión (kPa)</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("Los rangos de los escenarios son supuestos del equipo pendientes de fuente y validación.")

st.markdown(
    ui.strip(
        [
            ("Microgravedad (0 g)", f"{n0} pruebas", '<span style="color:#0F766E;font-weight:600">Cubierto</span>' if n0 > 0 else "Sin registros"),
            ("Gravedad normal (1 g)", f"{n1} pruebas", "Referencia"),
            (
                "Gravedad parcial (1/6 g · 3/8 g)",
                f"{npar} pruebas",
                '<span style="color:#B91C1C;font-weight:600">Brecha crítica</span>'
                if npar == 0
                else '<span style="color:#0F766E;font-weight:600">Cubierto</span>',
            ),
        ]
    ),
    unsafe_allow_html=True,
)

with st.expander("Malla de cobertura (conteos por bin)"):
    grid, provisional_cov = ui.coverage_df(df)
    ui.provisional_notice(provisional_cov, "Cobertura", "src/coverage.py")
    st.dataframe(grid, width="stretch")
    gaps = [(r, c) for r in grid.index for c in grid.columns if grid.loc[r, c] == 0]
    st.write(f"{len(gaps)} combinaciones sin ningún experimento.")
with st.expander("Datos faltantes en la tabla maestra"):
    st.dataframe(
        df[["o2_percent", "pressure_kpa", "flow_velocity"]].isna().sum().rename("filas sin dato"),
        width="stretch",
    )
