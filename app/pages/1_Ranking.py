import plotly.express as px
import streamlit as st

from data_loader import DEFAULT_WEIGHTS, load_master, mock_banner, rank

st.set_page_config(page_title="Ranking", page_icon="🔥", layout="wide")
st.title("Ranking de experimentos")

df, using_mock = load_master()
mock_banner(using_mock)

# --- Pesos ajustables ---
if "weights" not in st.session_state:
    st.session_state["weights"] = dict(DEFAULT_WEIGHTS)

with st.sidebar:
    st.header("Pesos del puntaje")
    for k in DEFAULT_WEIGHTS:
        st.session_state["weights"][k] = st.slider(
            k.capitalize(), 0.0, 1.0, float(st.session_state["weights"][k]), 0.05
        )
    if st.button("Restablecer pesos"):
        st.session_state["weights"] = dict(DEFAULT_WEIGHTS)
        st.rerun()

    st.header("Filtros")
    types = sorted(df["material_type"].dropna().unique())
    sel_types = st.multiselect("Tipo de material", types, default=types)

    def num_range(col, label):
        s = df[col].dropna()
        if s.empty or s.min() == s.max():
            return None
        return st.slider(label, float(s.min()), float(s.max()), (float(s.min()), float(s.max())))

    o2 = num_range("o2_percent", "Oxígeno (%)")
    pr = num_range("pressure_kpa", "Presión (kPa)")
    fl = num_range("flow_velocity", "Flujo")

# --- Filtrado tolerante a NaN: filas sin dato NO se descartan ---
f = df[df["material_type"].isin(sel_types)]
for col, rng in (("o2_percent", o2), ("pressure_kpa", pr), ("flow_velocity", fl)):
    if rng:
        f = f[f[col].isna() | f[col].between(*rng)]

if f.empty:
    st.info("Ningún experimento cumple los filtros.")
    st.stop()

ranked = rank(f, st.session_state["weights"]).reset_index(drop=True)
score_cols = [c for c in ranked.columns if c.startswith("score_") and c != "score_total"]

st.subheader("Tabla")
show = ["experiment_id", "psi_id", "title", "material_or_fuel", "o2_percent",
        "pressure_kpa", "flow_velocity", "flame_outcome", "flame_spread_rate", "score_total"]
show = [c for c in show if c in ranked.columns]
st.dataframe(
    ranked[show],
    use_container_width=True,
    hide_index=True,
    column_config={"score_total": st.column_config.ProgressColumn("Puntaje", min_value=0, max_value=1, format="%.2f")},
)

st.subheader("¿Por qué este orden? Desglose del puntaje")
if score_cols:
    long = ranked.head(15).melt(
        id_vars=["experiment_id"], value_vars=score_cols, var_name="componente", value_name="valor"
    )
    long["componente"] = long["componente"].str.replace("score_", "", regex=False)
    fig = px.bar(long, x="valor", y="experiment_id", color="componente", orientation="h")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=450, legend_title="Componente")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("El módulo de ranking aún no entrega el desglose por componente.")

st.caption("Fuente de cada fila: columnas psi_id y doi de la tabla maestra.")
