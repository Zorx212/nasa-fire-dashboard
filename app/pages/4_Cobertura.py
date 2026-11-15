import plotly.graph_objects as go
import streamlit as st

import ui
from data_loader import load_master, mock_banner

ui.setup("Cobertura")
df, using_mock = load_master()
ui.sidebar(df, using_mock)  # la cobertura evalúa TODOS los datos de la tabla maestra
ui.tabs(3)
mock_banner(using_mock)

nl = ui.zone_count(df, "Base Lunar / Rover")
nt = ui.zone_count(df, "Traje Espacial")
g = df["gravity_level"]
n0, n1 = int((g == 0).sum()), int((g == 1).sum())
npar = int(((g > 0) & (g < 1)).sum())
if nl < 5 or npar == 0:
    st.markdown(
        f'<div class="ban">Vacío de datos detectado: {nl} ensayos en Base Lunar (30–60% O₂, ≤70.3 kPa), '
        f'{nt} en Traje Espacial (90–100% O₂, ≤35 kPa) y {npar} ensayos en gravedad parcial real (1/6g · 3/8g).</div>',
        unsafe_allow_html=True,
    )

valid = df.dropna(subset=["o2_percent", "pressure_kpa"]).copy()
coord_groups = (
    valid.groupby(["o2_percent", "pressure_kpa"])
    .apply(
        lambda grp: "<br>".join(
            f"• {ui.clean_str(r.get('experiment_id'))} ({ui.clean_str(r.get('psi_id'))}) — "
            f"{ui.clean_str(r.get('material_or_fuel'))} [{ui.mat_label(r.get('material_type'))}] · {ui.outcome_label(r.get('flame_outcome'))}"
            for _, r in grp.iterrows()
        ),
        include_groups=False,
    )
    .to_dict()
)
coord_counts = valid.groupby(["o2_percent", "pressure_kpa"]).size().to_dict()

palette = {
    "sólido": ("#E84C22", "circle"),
    "solido": ("#E84C22", "circle"),
    "solid": ("#E84C22", "circle"),
    "gas": ("#1D4ED8", "diamond"),
    "líquido": ("#0F766E", "square"),
    "liquido": ("#0F766E", "square"),
    "liquid": ("#0F766E", "square"),
}
fig = go.Figure()
mat_types = list(dict.fromkeys(valid["material_type"].dropna().astype(str)))
for t in mat_types:
    d = valid[valid["material_type"].astype(str) == t]
    if d.empty:
        continue
    col, sym = palette.get(t.lower(), ("#0F766E", "square"))
    sizes = [11 + 3 * (coord_counts.get((row["o2_percent"], row["pressure_kpa"]), 1) - 1) for _, row in d.iterrows()]
    hover_texts = [
        f"<b>{ui.clean_str(row.get('experiment_id'))} · {ui.clean_str(row.get('psi_id'))}</b><br>"
        f"O₂ {row['o2_percent']:.1f}% · {row['pressure_kpa']:.1f} kPa<br>"
        f"<b>Ensayos en esta coordenada ({coord_counts.get((row['o2_percent'], row['pressure_kpa']), 1)}):</b><br>"
        f"{coord_groups.get((row['o2_percent'], row['pressure_kpa']), '')}"
        for _, row in d.iterrows()
    ]
    fig.add_trace(
        go.Scatter(
            x=d["o2_percent"],
            y=d["pressure_kpa"],
            mode="markers",
            name=ui.mat_label(t),
            marker=dict(color=col, size=sizes, symbol=sym, line=dict(width=1.5, color="#FFFFFF"), opacity=0.92),
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
        )
    )

active_scen = st.session_state.get("scen")
# Zonas y posición de anotaciones ancladas para que no se corten en 390px ni tapen puntos
zone_styles = (
    ("Base Lunar / Rover", "rgba(180,83,9,.11)", "#B45309", 45.0, 56.0, "center"),
    ("Traje Espacial", "rgba(232,76,34,.11)", "#B91C1C", 99.0, 22.0, "right"),
    ("ISS / Tierra", "rgba(29,78,216,.14)", "#1D4ED8", 24.5, 98.5, "left"),
)
for name, fill, line_col, ann_x, ann_y, x_anc in zone_styles:
    z = ui.SCEN[name]
    is_sel = active_scen == name
    fig.add_shape(
        type="rect",
        x0=z["o2"][0],
        x1=z["o2"][1],
        y0=z["p"][0],
        y1=z["p"][1],
        fillcolor=fill,
        line=dict(color=line_col, width=2.4 if is_sel else 1.6, dash="solid" if is_sel else "dash"),
    )
    fig.add_annotation(
        x=ann_x,
        y=ann_y,
        xanchor=x_anc,
        text=f"<b>{name}</b> ({ui.zone_count(df, name)})",
        showarrow=False,
        font=dict(size=10, color="#1E293B"),
        bgcolor="rgba(255,255,255,.92)",
        bordercolor=line_col,
        borderwidth=1,
        borderpad=3,
    )

y_top = max(118.0, float(valid["pressure_kpa"].max()) * 1.08) if not valid.empty else 118.0
fig = ui.style_fig(fig, 440)
fig.update_layout(
    title="Mapa 2D · Oxígeno (%) vs Presión (kPa)",
    xaxis_title="Oxígeno (%)",
    yaxis_title="Presión (kPa)",
    xaxis=dict(range=[-2, 103]),
    yaxis=dict(range=[-4, y_top]),
    legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, title_text=""),
    margin=dict(l=10, r=12, t=38, b=52),
)
st.plotly_chart(fig, width="stretch")
st.caption("Los rangos de los escenarios son supuestos del equipo pendientes de fuente y validación.")

c1, c2, c3 = st.columns(3)
c1.markdown(
    ui.card("Microgravedad (0g) " + ui.badge("Cubierto", "ok"), f"{n0} ensayos", "Condición de caída libre / ISS"),
    unsafe_allow_html=True,
)
c2.markdown(
    ui.card("Gravedad normal (1g) " + ui.badge("Referencia", "bl"), f"{n1} ensayos", "Base de comparación terrestre"),
    unsafe_allow_html=True,
)
c3.markdown(
    ui.card(
        "Gravedad parcial (1/6g · 3/8g) " + ui.badge("Brecha crítica" if npar == 0 else "Parcial", "wn"),
        f"{npar} ensayos",
        "Luna y Marte · pendiente misiones FM2 / LUCI" if npar == 0 else "Datos en gravedad reducida",
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
