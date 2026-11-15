from html import escape as E

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from data_loader import load_master, mock_banner

ui.setup("Comparación")
df, using_mock = load_master()
f, _ = ui.sidebar(df, using_mock)
ui.tabs(1)
mock_banner(using_mock)

df_indexed = df.drop_duplicates(subset=["experiment_id"]).set_index("experiment_id")
opts = df_indexed.index.tolist()
filtered_opts = [i for i in f["experiment_id"].tolist() if i in df_indexed.index]
default_opts = filtered_opts[:2] if len(filtered_opts) >= 2 else opts[:2]

if len(f) < len(df):
    st.caption(f"Filtro lateral activo: {len(filtered_opts)} de {len(opts)} ensayos coinciden (puedes comparar cualquiera de la tabla maestra).")

chosen = st.multiselect(
    "Elige 2 o 3 experimentos",
    opts,
    default=default_opts,
    max_selections=3,
    format_func=lambda i: f"{i} · {ui.clean_str(df_indexed.loc[i, 'psi_id'])} · {ui.clean_str(df_indexed.loc[i, 'material_or_fuel'])}",
)
if len(chosen) < 2:
    st.info("Selecciona al menos 2 experimentos.")
    st.stop()
sel = df_indexed.loc[chosen]


def line(name, fn):
    vals = [fn(r) for _, r in sel.iterrows()]
    diff = len(set(vals)) > 1
    return f'<tr class="{"d" if diff else ""}"><td>{E(name)}</td>' + "".join(f"<td>{v}</td>" for v in vals) + "</tr>"


head = "".join(
    f'<th class="mono">{E(str(i))} · {E(ui.clean_str(r.get("psi_id")))}<br>{ui.doi_pill(r.get("doi"))}</th>'
    for i, r in sel.iterrows()
)


def fmt_spread(r):
    u = ui.clean_str(r.get("spread_rate_unit"), default="")
    suffix = f" {u}" if u else ""
    return f'{ui.badge(r.get("flame_outcome"))} <span class="n" style="margin-left:6px">{ui.num(r.get("flame_spread_rate"), 2, suffix)}</span>'


body = (
    line("Material", lambda r: f'<b>{E(ui.clean_str(r.get("material_or_fuel")))}</b> ({E(ui.clean_str(r.get("material_type")))})')
    + line("Oxígeno (%)", lambda r: f'<span class="n">{ui.num(r.get("o2_percent"), 1, "% O₂")}</span>')
    + line("Presión (kPa)", lambda r: f'<span class="n">{ui.num(r.get("pressure_kpa"), 1, " kPa")}</span>')
    + line("Flujo / Gravedad", lambda r: f'<span class="n">{ui.num(r.get("flow_velocity"), 1, " cm/s")} · {ui.fmt_gravity(r.get("gravity_level"))}</span>')
    + line("Resultado y propagación", fmt_spread)
    + line("Fuente documental", lambda r: f'<span class="n">{E(ui.clean_str(r.get("source_file")))} · pág. {ui.num(r.get("source_page"), 0)}</span>')
)

st.markdown(
    f'<div class="card"><b>Matriz de especificaciones</b>'
    f'<div style="overflow-x:auto"><table class="cmp"><thead><tr><th>Variable</th>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    f'<small style="color:#B45309;display:block;margin-top:10px">'
    f'Las filas sombreadas señalan diferencias. Cada variable conserva su unidad; la comparación no mezcla escalas.</small></div>',
    unsafe_allow_html=True,
)

# --- Gráficas comparativas (2 secciones: Small Multiples por variable con eje independiente + Comportamiento de llama) ---
exp_labels = [f"{exp_id} ({ui.clean_str(sel.loc[exp_id, 'psi_id'])})" for exp_id in chosen]
bar_palette = ["#1D4ED8", "#E84C22", "#0F766E"]

left_col, right_col = st.columns([1.35, 1.0])

with left_col:
    st.markdown("**Condiciones de prueba (escalas independientes por unidad)**")
    sm_cols = st.columns(3)
    cond_specs = [
        ("o2_percent", "Oxígeno", "%", 1),
        ("pressure_kpa", "Presión", " kPa", 1),
        ("flow_velocity", "Flujo", " cm/s", 1),
    ]
    for sc_col, (col_name, title_lbl, unit_lbl, dec) in zip(sm_cols, cond_specs):
        raw_vals = [pd.to_numeric(pd.Series([sel.loc[eid].get(col_name)]), errors="coerce").iloc[0] for eid in chosen]
        y_vals = [None if pd.isna(v) else float(v) for v in raw_vals]
        txt_vals = ["" if pd.isna(v) else f"{float(v):.{dec}f}{unit_lbl}" for v in raw_vals]
        finite_vals = [v for v in y_vals if v is not None]
        y_max = max(finite_vals) * 1.28 if finite_vals and max(finite_vals) > 0 else 10.0

        fig_c = go.Figure(
            go.Bar(
                x=chosen,
                y=y_vals,
                text=txt_vals,
                textposition="outside",
                marker_color=bar_palette[: len(chosen)],
                hovertemplate="%{x}: %{text}<extra></extra>",
            )
        )
        for eid, v in zip(chosen, y_vals):
            if v is None:
                fig_c.add_annotation(
                    x=eid,
                    y=y_max * 0.15,
                    text="sin dato",
                    showarrow=False,
                    font=dict(size=10.5, color="#64748B"),
                    bgcolor="#F1F5F9",
                    borderpad=2,
                )
        fig_c.update_layout(
            title=f"{title_lbl} ({unit_lbl.strip()})",
            yaxis=dict(range=[0, y_max], title=""),
            xaxis=dict(title=""),
            showlegend=False,
            margin=dict(l=6, r=6, t=34, b=6),
        )
        with sc_col:
            st.plotly_chart(ui.style_fig(fig_c, 235), width="stretch")

with right_col:
    st.markdown("**Comportamiento de llama (tasa de propagación)**")
    units_present = {
        ui.clean_str(sel.loc[eid].get("spread_rate_unit"), default="")
        for eid in chosen
        if not pd.isna(pd.to_numeric(pd.Series([sel.loc[eid].get("flame_spread_rate")]), errors="coerce").iloc[0])
    }
    units_present.discard("")
    if len(units_present) > 1:
        st.warning("Los ensayos seleccionados tienen unidades de propagación distintas; no se grafican en un mismo eje.")
    else:
        unit_str = next(iter(units_present), ui.clean_str(sel.iloc[0].get("spread_rate_unit"), "mm/s"))
        sp_raw = [pd.to_numeric(pd.Series([sel.loc[eid].get("flame_spread_rate")]), errors="coerce").iloc[0] for eid in chosen]
        sp_y = [None if pd.isna(v) else float(v) for v in sp_raw]
        sp_outcomes = [ui.clean_str(sel.loc[eid].get("flame_outcome"), "Sin dato") for eid in chosen]
        sp_colors = [
            "#B91C1C" if ui.kind(o) == "dg" else "#15803D" if ui.kind(o) == "ok" else "#1D4ED8"
            for o in sp_outcomes
        ]
        sp_texts = [
            "" if pd.isna(v) else f"{float(v):.2f} {unit_str} · {o}"
            for v, o in zip(sp_raw, sp_outcomes)
        ]
        finite_sp = [v for v in sp_y if v is not None]
        sp_max = max(finite_sp) * 1.28 if finite_sp and max(finite_sp) > 0 else 5.0

        fig_sp = go.Figure(
            go.Bar(
                x=exp_labels,
                y=sp_y,
                text=sp_texts,
                textposition="outside",
                marker_color=sp_colors,
                hovertemplate="%{x}<br>%{text}<extra></extra>",
            )
        )
        for lbl, v, o in zip(exp_labels, sp_y, sp_outcomes):
            if v is None:
                fig_sp.add_annotation(
                    x=lbl,
                    y=sp_max * 0.16,
                    text=f"sin dato ({o})",
                    showarrow=False,
                    font=dict(size=11, color="#15803D" if ui.kind(o) == "ok" else "#64748B"),
                    bgcolor="#F0FDF4" if ui.kind(o) == "ok" else "#F1F5F9",
                    borderpad=3,
                )
        fig_sp.update_layout(
            title=f"Velocidad de propagación ({unit_str})",
            yaxis=dict(range=[0, sp_max], title=unit_str),
            xaxis=dict(title=""),
            showlegend=False,
            margin=dict(l=10, r=10, t=34, b=10),
        )
        st.plotly_chart(ui.style_fig(fig_sp, 235), width="stretch")
