from html import escape as E

import plotly.express as px
import streamlit as st

import ui
from data_loader import load_master, mock_banner

ui.setup("Ranking")
df, using_mock = load_master()
f, w = ui.sidebar(df, using_mock)
ui.tabs(0)
mock_banner(using_mock)
scen = st.session_state.get("scen")
spin_seq = st.session_state.get("_spin_seq", 0)
cnt_cls = "cnt cnt-a" if spin_seq % 2 == 1 else "cnt cnt-b"

if sum(w.values()) <= 0:
    st.info("Todos los pesos del ranking están en 0. Sube al menos un criterio en «Ajustar pesos del ranking» para priorizar.")

using_nearest = False
if f.empty:
    if not scen:
        st.info("Ningún experimento cumple los filtros seleccionados. Ajusta los rangos o limpia los filtros en el panel lateral.")
        st.stop()
    using_nearest = True
    st.warning(f"Ningún experimento cae dentro de «{scen}». Se muestran los 10 más cercanos.")
    mat_filter = st.session_state.get("f_mat", "Todos")
    base_df = df if mat_filter == "Todos" else df[df["material_type"].astype(str) == mat_filter]
    f = ui.nearest(base_df if not base_df.empty else df, scen)

ranked_df, provisional = ui.rank_df(f, w)
ui.provisional_notice(provisional, "Ranking", "src/ranking.py")
ranked = ui.best_per_study_first(ranked_df).reset_index(drop=True)
_, _, pp = ui.outcome_counts(f["flame_outcome"])
n_psi = int(f["psi_id"].nunique()) if "psi_id" in f.columns else 0

top = ranked.head(15).reset_index(drop=True)
cur_sel = st.session_state.get("rk_sel", 0)
if not isinstance(cur_sel, int) or cur_sel < 0 or cur_sel >= len(top):
    cur_sel = 0
    st.session_state["rk_sel"] = 0

c1_val = (
    f'<span class="{cnt_cls}" style="--n:0"></span> exactos<!-- 0 exactos -->'
    if using_nearest
    else f'<span class="{cnt_cls}" style="--n:{len(f)}"></span> pruebas'
)
c1_sub = (
    f'Mostrando <span class="{cnt_cls}" style="--n:{len(f)}"></span> cercanos · <span class="{cnt_cls}" style="--n:{n_psi}"></span> estudios PSI'
    if using_nearest
    else f'<span class="{cnt_cls}" style="--n:{n_psi}"></span> estudios PSI'
)
c2_val = f'<span class="{cnt_cls}" style="--n:{pp}"></span> % propagó' if pp is not None else "Sin dato"
c2_sub = f'<span class="{cnt_cls}" style="--n:{100 - pp}"></span> % se extinguió' if pp is not None else "Sin registros suficientes"

if scen in ui.SCEN:
    n_zone = ui.zone_count(df, scen)
    c3_lbl = f"Cobertura de {E(scen)}"
    c3_val = "Sin cobertura" if n_zone == 0 else "Parcial" if n_zone < 5 else "Amplia"
    c3_sub = f'<span class="{cnt_cls}" style="--n:{n_zone}"></span> pruebas en la zona'
else:
    c3_lbl = "Estado de cobertura"
    c3_val = "Sin escenario"
    c3_sub = "Elige un escenario en el menú lateral para evaluar su zona."

st.markdown(
    ui.strip(
        [
            ("Pruebas coincidentes", c1_val, c1_sub),
            ("Resultado dominante", c2_val, c2_sub),
            (c3_lbl, c3_val, c3_sub),
        ]
    ),
    unsafe_allow_html=True,
)

sc = [k for k in ui.COMP if f"score_{k}" in ranked.columns]
tot = max(sum(w[k] for k in sc), 1e-9)
rows = ""
for i, r in top.iterrows():
    score_val = r.get("score_total", 0.0)
    score = 0 if score_val != score_val else max(0, min(100, round(100 * float(score_val))))
    psi_id = E(ui.clean_str(r.get("psi_id")))
    mat = E(ui.clean_str(r.get("material_or_fuel")))
    mtype = E(ui.mat_label(r.get("material_type")))
    row_cls = ' class="sel"' if i == cur_sel else ""
    rows += (
        f"<tr{row_cls}>"
        f'<td class="n">{i + 1}</td>'
        f'<td class="n">{psi_id}</td>'
        f"<td><b>{mat}</b> <small style='color:#64748B'>({mtype})</small></td>"
        f'<td class="n">{ui.num(r.get("o2_percent"), 1, " %")}</td>'
        f'<td class="n">{ui.num(r.get("pressure_kpa"), 1, " kPa")}</td>'
        f'<td class="n">{ui.num(r.get("flow_velocity"), 1, " cm/s")}</td>'
        f'<td>{ui.badge(r.get("flame_outcome"))}</td>'
        f'<td><div class="score-cell"><span class="score-track"><i style="width:{score}%"></i></span><span class="n">{score}/100</span></div></td>'
        f'<td>{ui.doi_pill(r.get("doi"))}</td>'
        f"</tr>"
    )
head = "".join(
    f"<th>{h}</th>"
    for h in ["#", "Estudio PSI", "Material", "O₂ (%)", "Presión", "Flujo", "Resultado", "Puntaje", "DOI"]
)
table_html = (
    f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;gap:12px;flex-wrap:wrap">'
    f'<h3 style="margin:0">Ranking de experimentos y materiales</h3>'
    f'<span style="color:#64748B;font-size:12px">Mostrando {len(top)} de {len(ranked)} pruebas</span></div>'
    f'<div style="overflow-x:auto"><table class="rk"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
)
st.markdown(ui.ficha(f"Ranking · {len(ranked)} pruebas", table_html), unsafe_allow_html=True)

if sc:
    with st.container(key="rk_chart_card"):
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
            labels={"aporte": "Aporte ponderado al puntaje", "experiment_id": "Prueba", "componente": "Componente"},
        )
        fig.update_layout(
            title="Desglose ponderado del puntaje (primeros 10)",
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

sel_idx = st.selectbox(
    "Detalle de la prueba",
    range(len(top)),
    key="rk_sel",
    format_func=lambda idx: f"{ui.clean_str(top.loc[idx, 'experiment_id'])} · {ui.clean_str(top.loc[idx, 'psi_id'])} · {ui.clean_str(top.loc[idx, 'material_or_fuel'])}",
)
r = top.loc[sel_idx]
psi_raw = ui.clean_str(r.get("psi_id"))
exp_raw = ui.clean_str(r.get("experiment_id"))
mat_raw = ui.clean_str(r.get("material_or_fuel"))
unit_str = ui.clean_str(r.get("spread_rate_unit"), default="")
unit_suffix = f" {unit_str}" if unit_str else ""
src_file = E(ui.clean_str(r.get("source_file")))
src_page = ui.num(r.get("source_page"), 0)
lic_str = E(ui.clean_str(r.get("license")))

score_tot_val = r.get("score_total", 0.0)
score_pct = 0 if score_tot_val != score_tot_val else max(0, min(100, round(100 * float(score_tot_val))))
if sc:
    segs_html = "".join(
        f'<i style="width:{max(0.0, min(100.0, 100.0 * (0.0 if r.get(f"score_{k}", 0.0) != r.get(f"score_{k}", 0.0) else float(r.get(f"score_{k}", 0.0))) * w[k] / tot)):.2f}%;background:{ui.COMP[k]}"></i>'
        for k in sc
    )
else:
    segs_html = f'<i style="width:{score_pct}%;background:#E84C22"></i>'

specs_html = ui.dot_specs(
    [
        ("O₂", ui.num(r.get("o2_percent"), 1, " %")),
        ("Presión", ui.num(r.get("pressure_kpa"), 1, " kPa")),
        ("Flujo", ui.num(r.get("flow_velocity"), 1, " cm/s")),
        ("Gravedad", ui.fmt_gravity(r.get("gravity_level"))),
        ("Propagación", ui.num(r.get("flame_spread_rate"), 2, unit_suffix)),
    ]
)
loc_svg = ui.locator(df, top.iloc[[sel_idx]])
detail_body = (
    f'<div class="f-split"><div class="f-main">'
    f'<h3 class="f-title">{E(mat_raw)}</h3>'
    f'<div>{ui.badge(r.get("flame_outcome"))}</div>'
    f'{specs_html}'
    f'<div class="stacked-row"><div class="stacked-bar">{segs_html}</div><span class="mono" style="font-size:13px;font-weight:500">{score_pct}/100</span></div>'
    f'<div class="f-foot">Fuente: <span class="mono">{src_file} · p. {src_page}</span> · Licencia: {lic_str} · {ui.doi_pill(r.get("doi"))}</div>'
    f'</div><div class="f-loc">{loc_svg}</div></div>'
)
st.markdown(ui.ficha(f"{psi_raw} · {exp_raw}", detail_body), unsafe_allow_html=True)
