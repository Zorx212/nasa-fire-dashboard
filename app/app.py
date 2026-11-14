import streamlit as st

from data_loader import DEFAULT_WEIGHTS, load_insights, load_master, mock_banner

st.set_page_config(page_title="Fuego en microgravedad", page_icon="🔥", layout="wide")

df, using_mock = load_master()
insights, _ = load_insights()

if "weights" not in st.session_state:
    st.session_state["weights"] = dict(DEFAULT_WEIGHTS)

st.title("🔥 Llama en caída libre")
st.caption("Seguridad contra incendios para exploración espacial, con datos de combustión en microgravedad de NASA PSI.")
mock_banner(using_mock)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Experimentos", len(df))
c2.metric("Investigaciones PSI", df["psi_id"].nunique())
c3.metric("Insights con cita", len(insights))
c4.metric("Rango de O₂ (%)", f"{df['o2_percent'].min():.0f}–{df['o2_percent'].max():.0f}")

st.markdown(
    """
**Pregunta que responde:** ¿qué sabemos del fuego en microgravedad bajo estas condiciones y qué tan confiable es?

Usa el menú lateral:
1. **Ranking**: experimentos con puntaje explicable y pesos ajustables.
2. **Comparación**: 2 o 3 experimentos lado a lado.
3. **Insights**: conclusiones de seguridad con fuente (ID PSI y DOI).
4. **Cobertura**: qué condiciones están cubiertas y cuáles no.
"""
)
