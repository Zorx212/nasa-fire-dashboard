import plotly.express as px
import streamlit as st

from data_loader import coverage_grid, load_master, mock_banner

st.set_page_config(page_title="Cobertura", page_icon="🔥", layout="wide")
st.title("Cobertura y vacíos")
st.caption("Qué condiciones están cubiertas por los datos y cuáles no.")

df, using_mock = load_master()
mock_banner(using_mock)

grid = coverage_grid(df)

fig = px.imshow(
    grid, text_auto=True, aspect="auto", color_continuous_scale="Oranges",
    labels=dict(x="Oxígeno (%)", y="Presión (kPa)", color="Experimentos"),
)
st.plotly_chart(fig, use_container_width=True)

gaps = [(str(r), str(c)) for r in grid.index for c in grid.columns if grid.loc[r, c] == 0]
st.subheader("Vacíos")
if gaps:
    st.write(f"{len(gaps)} combinaciones sin ningún experimento:")
    for p, o in gaps:
        st.markdown(f"- No hay experimentos con presión **{p}** kPa y oxígeno **{o}** %")
else:
    st.success("Todas las celdas tienen al menos un experimento.")

missing = df[["o2_percent", "pressure_kpa", "flow_velocity"]].isna().sum()
st.subheader("Datos faltantes en la tabla maestra")
st.dataframe(missing.rename("filas sin dato"), use_container_width=True)
