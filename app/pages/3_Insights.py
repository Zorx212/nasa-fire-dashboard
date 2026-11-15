import streamlit as st

from data_loader import citation, load_insights, mock_banner

st.set_page_config(page_title="Insights", page_icon="🔥", layout="wide")
st.title("Insights de seguridad")
st.caption("Cada afirmación muestra su fuente. Las respuestas están precalculadas: no se llama a ningún LLM desde la app.")

insights, using_mock = load_insights()
mock_banner(using_mock)

scopes = sorted({i.get("scope", "") for i in insights})
scope = st.radio("Mostrar", ["todos"] + scopes, horizontal=True)

BADGE = {"alta": "🟢 alta", "media": "🟡 media", "baja": "🔴 baja"}

for ins in insights:
    if scope != "todos" and ins.get("scope") != scope:
        continue
    with st.container(border=True):
        st.subheader(ins.get("title", ins["id"]))
        st.caption(
            f"{ins.get('scope', '')} · {', '.join(ins.get('psi_ids', []))} · "
            f"confianza: {BADGE.get(ins.get('confidence', ''), ins.get('confidence', '?'))}"
        )
        claims = ins.get("claims", [])
        if not claims:
            st.info("No hay datos suficientes.")
        for c in claims:
            if not (c.get("psi_id") and c.get("doi")):
                st.error("Afirmación sin fuente: no debería publicarse.")
            st.markdown(f"- {c['text']}  \n  {citation(c)}")
