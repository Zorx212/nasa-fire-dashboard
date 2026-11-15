import plotly.express as px
import streamlit as st

from data_loader import load_master, mock_banner

st.set_page_config(page_title="Comparación", page_icon="🔥", layout="wide")
st.title("Comparación de experimentos")

df, using_mock = load_master()
mock_banner(using_mock)

options = df["experiment_id"].tolist()
chosen = st.multiselect("Elige 2 o 3 experimentos", options, default=options[:2], max_selections=3)

if len(chosen) < 2:
    st.info("Selecciona al menos 2 experimentos.")
    st.stop()

sel = df[df["experiment_id"].isin(chosen)]

cols = st.columns(len(chosen))
for col, (_, r) in zip(cols, sel.set_index("experiment_id").loc[chosen].reset_index().iterrows()):
    with col:
        st.subheader(r["experiment_id"])
        st.caption(f"{r['psi_id']} · [{r['doi']}](https://doi.org/{r['doi']})")
        st.write(f"**{r['material_or_fuel']}** ({r['material_type']})")
        st.metric("O₂ (%)", "—" if r["o2_percent"] != r["o2_percent"] else f"{r['o2_percent']:.0f}")
        st.metric("Presión (kPa)", "—" if r["pressure_kpa"] != r["pressure_kpa"] else f"{r['pressure_kpa']:.1f}")
        st.metric("Resultado", r["flame_outcome"])
        sp = r["flame_spread_rate"]
        st.metric("Propagación", "sin dato" if sp != sp else f"{sp:.2f} {r.get('spread_rate_unit', '')}")

st.subheader("Diferencias clave")
diff = sel.set_index("experiment_id").T
diff = diff.loc[["o2_percent", "pressure_kpa", "flow_velocity", "flame_outcome", "flame_spread_rate"]]
st.dataframe(diff, use_container_width=True)

st.subheader("Gráficas")
g1, g2 = st.columns(2)
with g1:
    d = sel.dropna(subset=["flame_spread_rate"])
    if d.empty:
        st.info("Sin datos de velocidad de propagación en la selección.")
    else:
        st.plotly_chart(
            px.bar(d, x="experiment_id", y="flame_spread_rate", color="psi_id",
                   title="Velocidad de propagación"),
            use_container_width=True,
        )
with g2:
    d = sel.dropna(subset=["o2_percent", "pressure_kpa"])
    if d.empty:
        st.info("Sin datos de O₂ y presión en la selección.")
    else:
        st.plotly_chart(
            px.scatter(d, x="o2_percent", y="pressure_kpa", color="flame_outcome",
                       symbol="psi_id", hover_name="experiment_id", size_max=14,
                       title="Condiciones y resultado"),
            use_container_width=True,
        )
