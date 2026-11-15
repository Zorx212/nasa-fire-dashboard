from html import escape as E

import plotly.express as px
import streamlit as st

import ui
from data_loader import load_master, mock_banner, rank

ui.setup("Ranking")
df, using_mock = load_master()
f, w = ui.sidebar(df, using_mock)
ui.tabs(0)
mock_banner(using_mock)
scen = st.session_state.get("scen")

using_nearest = False
if f.empty:
    if not scen:
        st.info("Ningún experimento cumple los filtros seleccionados.")
        st.stop()
    using_nearest = True
    st.warning(f"Ningún experimento cae dentro de «{scen}». Se muestran los 10 más cercanos.")
    mat_filter = st.session_state.get("f_mat", "Todos")
    base_df = df if mat_filter == "Todos" else df[df["material_type"].astype(str) == mat_filter]
    f = ui.nearest(base_df if not base_df.empty else df, scen)

ranked = rank(f, w).reset_index(drop=True)
_, _, pp = ui.outcome_counts(f["flame_outcome"])

c1, c2, c3 = st.columns(3)
if using_nearest:
    c1.markdown(
        ui.card("Ensayos coincidentes", "0 exactos", f"Mostrando {len(f)} cercanos · {f['psi_id'].nunique()} estudios PSI"),
        unsafe_allow_html=True,
    )
else:
    c1.markdown(
        ui.card("Ensayos coincidentes", f"{len(f)} ensayos", f"{f['psi_id'].nunique()} estudios PSI"),
        unsafe_allow_html=True,
    )

bar = (
    f'<div class="prop"><i style="width:{pp}%;background:#B91C1C"></i>'
    f'<i style="width:{100-pp}%;background:#15803D"></i></div>'
    if pp is not None
    else ""
)
c2.markdown(
    ui.card(
        "Resultado dominante",
        f'{pp}% <span style="font-size:15px;font-weight:500;color:#475569">propagó · {100-pp}% se extinguió</span>'
        if pp is not None
        else "Sin dato",
        bar,
    ),
    unsafe_allow_html=True,
)
if scen in ui.SCEN:
    n = ui.zone_count(df, scen)
    lab = "Sin cobertura" if n == 0 else "Cobertura parcial" if n < 5 else "Cobertura amplia"
    b_kind = "dg" if n == 0 else "wn" if n < 5 else "ok"
    c3.markdown(
        ui.card("Estado de cobertura", lab, f"{ui.badge(scen, b_kind)} · {n} ensayos en la zona"),
        unsafe_allow_html=True,
    )
else:
    c3.markdown(
        ui.card("Estado de cobertura", "Sin escenario", "Elige uno en el menú lateral"),
        unsafe_allow_html=True,
    )

sc = [k for k in ui.COMP if f"score_{k}" in ranked.columns]
tot = max(sum(w[k] for k in sc), 1e-9)
rows = ""
for i, r in ranked.head(15).iterrows():
    score_val = r.get("score_total", 0.0)
    score = 0 if score_val != score_val else max(0, min(100, round(100 * float(score_val))))
    psi_id = E(ui.clean_str(r.get("psi_id")))
    mat = E(ui.clean_str(r.get("material_or_fuel")))
    mtype = E(ui.clean_str(r.get("material_type")))
    row_cls = ' class="top-row"' if i == 0 else ""
    rows += (
        f"<tr{row_cls}>"
        f'<td class="n">{i+1}</td>'
        f'<td class="n">{psi_id}</td>'
        f"<td><b>{mat}</b> <small style='color:#64748B'>({mtype})</small></td>"
        f'<td class="n">{ui.num(r.get("o2_percent"), 1, "%")}</td>'
        f'<td class="n">{ui.num(r.get("pressure_kpa"), 1, " kPa")}</td>'
        f'<td class="n">{ui.num(r.get("flow_velocity"), 1, " cm/s")}</td>'
        f'<td>{ui.badge(r.get("flame_outcome"))}</td>'
        f'<td><div class="score-cell"><span class="score-track"><i style="width:{score}%"></i></span>'
        f'<span class="n">{score}/100</span></div></td>'
        f'<td>{ui.doi_pill(r.get("doi"))}</td>'
        f"</tr>"
    )
head = "".join(
    f"<th>{h}</th>"
    for h in ["#", "ID PSI", "Material", "O₂ (%)", "Presión", "Flujo", "Resultado", "Puntaje", "DOI"]
)
st.markdown(
    f'<div class="card" style="padding-bottom:10px">'
    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
    f'<b>Ranking de experimentos y materiales</b>'
    f'<small style="color:#64748B">Mostrando {min(15, len(ranked))} de {len(ranked)} ensayos</small></div>'
    f'<div style="overflow-x:auto"><table class="rk">'
    f"<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div></div>",
    unsafe_allow_html=True,
)

if sc:
    breakdown = ranked.head(10).melt(
        id_vars=["experiment_id"],
        value_vars=[f"score_{k}" for k in sc],
        var_name="componente",
        value_name="valor",
    )
    breakdown["componente"] = breakdown["componente"].str.removeprefix("score_")
    breakdown["aporte"] = breakdown.apply(
        lambda row: float(row["valor"] if row["valor"] == row["valor"] else 0.0) * w[row["componente"]] / tot,
        axis=1,
    )
    fig = px.bar(
        breakdown,
        x="aporte",
        y="experiment_id",
        color="componente",
        orientation="h",
        barmode="stack",
        color_discrete_map=ui.COMP,
        labels={"aporte": "Aporte ponderado al puntaje", "experiment_id": "Ensayo", "componente": "Componente"},
    )
    fig.update_layout(
        title="Desglose ponderado del puntaje (Top 10)",
        xaxis=dict(range=[0, 1], tickformat=".0%"),
        yaxis={"categoryorder": "total ascending"},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title_text=""),
    )
    st.plotly_chart(ui.style_fig(fig, 310), width="stretch")
    leg = "".join(
        f'<span><i class="comp-dot" style="background:{c}"></i>{E(ui.COMP_LABELS.get(k, k))} ({int(round(100 * w[k] / tot))}%)</span>'
        for k, c in ui.COMP.items()
        if k in sc
    )
    st.markdown(f'<div class="comp-legend">{leg}</div>', unsafe_allow_html=True)

top = ranked.head(15).reset_index(drop=True)
sel_idx = st.selectbox(
    "Detalle del ensayo",
    range(len(top)),
    format_func=lambda idx: f"{ui.clean_str(top.loc[idx, 'experiment_id'])} · {ui.clean_str(top.loc[idx, 'psi_id'])} · {ui.clean_str(top.loc[idx, 'material_or_fuel'])}",
)
r = top.loc[sel_idx]
unit_str = ui.clean_str(r.get("spread_rate_unit"), default="")
unit_suffix = f" {unit_str}" if unit_str else ""
src_file = E(ui.clean_str(r.get("source_file")))
src_page = ui.num(r.get("source_page"), 0)

d1, d2, d3, d4 = st.columns(4)
d1.markdown(
    ui.card("Tasa de propagación", ui.num(r.get("flame_spread_rate"), 2, unit_suffix), E(ui.clean_str(r.get("title"), ""))),
    unsafe_allow_html=True,
)
d2.markdown(
    ui.card("Gravedad", ui.fmt_gravity(r.get("gravity_level")), "Nivel gravitacional del ensayo"),
    unsafe_allow_html=True,
)
d3.markdown(
    ui.card("Fuente documental", f"<span style='font-size:15px'>{src_file} · pág. {src_page}</span>", f"ID: {E(ui.clean_str(r.get('experiment_id')))}"),
    unsafe_allow_html=True,
)
d4.markdown(
    ui.card("Licencia y notas", E(ui.clean_str(r.get("license"))), E(ui.clean_str(r.get("notes"), ""))),
    unsafe_allow_html=True,
)
