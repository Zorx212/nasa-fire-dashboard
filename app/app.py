import streamlit as st

import ui
from data_loader import load_master, mock_banner

ui.setup("Flame in Freefall")
df, using_mock = load_master()
raw_insights, insights_mock = ui.load_insights_any()
insights_list, _ = ui.extract_insights(raw_insights)
f, _ = ui.sidebar(df, using_mock)
ui.tabs(-1)

st.title("Flame in Freefall")
st.caption("NASA PSI · Analítica de seguridad contra incendios en microgravedad")
mock_banner(using_mock or insights_mock)

n_studies = int(df["psi_id"].nunique()) if "psi_id" in df.columns else 0
g = df["gravity_level"] if "gravity_level" in df.columns else df.index * 0
n_partial = int(((g > 0) & (g < 1)).sum())
_, _, pp = ui.outcome_counts(df["flame_outcome"]) if "flame_outcome" in df.columns else (0, 0, None)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    ui.card("Ensayos disponibles", f"{len(df)} ensayos", f"{len(f)} coinciden con los filtros activos"),
    unsafe_allow_html=True,
)
c2.markdown(
    ui.card("Estudios PSI", f"{n_studies} estudios", f"{pp}% con propagación sostenida" if pp is not None else "En tabla maestra"),
    unsafe_allow_html=True,
)
c3.markdown(
    ui.card("Respuestas precalculadas", f"{len(insights_list)} hallazgos", "Con citas PSI, DOI y página"),
    unsafe_allow_html=True,
)
c4.markdown(
    ui.card(
        "Gravedad parcial (1/6g · 3/8g)",
        f"{n_partial} ensayos",
        ui.badge("Brecha crítica · 0 en Luna/Marte" if n_partial == 0 else "Datos disponibles", "wn" if n_partial == 0 else "ok"),
    ),
    unsafe_allow_html=True,
)

st.markdown("### Explora la evidencia")
st.caption("Selecciona una vista o usa las pestañas superiores para rankear ensayos, comparar condiciones, revisar hallazgos con citas y detectar vacíos de cobertura.")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        ui.card(
            "01 · Veredicto y relevancia",
            "Ranking",
            "Puntaje explicable con pesos ajustables y detalle por ensayo.",
            kpi=False,
        ),
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Ranking.py", label="Abrir Ranking →", width="stretch")
with m2:
    st.markdown(
        ui.card(
            "02 · Contraste lado a lado",
            "Comparación",
            "Matriz de especificaciones y gráficas por variable alineando unidades.",
            kpi=False,
        ),
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Comparacion.py", label="Abrir Comparación →", width="stretch")
with m3:
    st.markdown(
        ui.card(
            "03 · Síntesis verificada",
            "Insights",
            "Hallazgos precalculados con nivel de evidencia y cita textual.",
            kpi=False,
        ),
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Insights.py", label="Abrir Insights →", width="stretch")
with m4:
    st.markdown(
        ui.card(
            "04 · Brechas experimentales",
            "Cobertura y vacíos",
            "Mapa 2D Oxígeno vs. Presión, zonas de escenario y conteo por gravedad.",
            kpi=False,
        ),
        unsafe_allow_html=True,
    )
    st.page_link("pages/4_Cobertura.py", label="Abrir Cobertura →", width="stretch")

if using_mock:
    st.info(
        "No se encontró data/processed/master_table.csv. Esta vista usa los datos de demostración de data/mock; "
        "el reporte PSI-107 del repositorio aún no está normalizado a la tabla de experimentos."
    )
