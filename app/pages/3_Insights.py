from html import escape as E

import streamlit as st

import ui
from data_loader import load_master, mock_banner

ui.setup("Insights")
df, using_mock_df = load_master()
ui.sidebar(df, using_mock_df)
ui.tabs(2)
raw_insights, using_mock = ui.load_insights_any()
mock_banner(using_mock)
st.caption("Cada afirmación muestra su fuente. Respuestas precalculadas: no se llama a ningún LLM desde la app.")

insights_list, meta = ui.extract_insights(raw_insights)
if meta.get("model"):
    st.caption(f"Modelo de extracción offline: `{meta['model']}` · prompt v{meta.get('prompt_version', '1.0')}")

questions = [
    "Todas las respuestas precalculadas",
    "¿Qué cambia al subir O₂ a ≥30%?",
    "¿Qué materiales sólidos propagan más rápido?",
    "¿Qué sabemos de gravedad parcial?",
]
question = st.radio("Preguntas sugeridas", questions, horizontal=True)

items = [ui.norm_insight(i) for i in insights_list]
question_terms = {
    questions[1]: ("oxígeno", "o2", "o₂", "oxygen", "30%"),
    questions[2]: ("sólido", "solido", "solid", "pmma", "celulosa", "material"),
    questions[3]: ("gravedad parcial", "partial gravity", "1/6g", "3/8g", "lunar", "marte"),
}
if question != questions[0]:
    terms = question_terms[question]
    items = [
        item
        for item in items
        if any(term in (item["title"] + " " + item["text"] + " " + item.get("explanation", "")).lower() for term in terms)
    ]
    if not items:
        st.info("No hay una respuesta precalculada para esta pregunta. La app no consulta un LLM en vivo.")

scopes = sorted({i["scope"] for i in items if i["scope"]})
scope = (
    st.radio("Mostrar", ["todos"] + scopes, horizontal=True, format_func=ui.scope_label)
    if scopes
    else "todos"
)

for idx, it in enumerate(items):
    if scope != "todos" and it["scope"] != scope:
        continue
    foot_pills = []
    for c in it["cites"][:4]:
        psi = E(ui.clean_str(c.get("psi_id"), "?"))
        doi_raw = ui.clean_str(c.get("doi"), "")
        page_str = E(ui.clean_str(c.get("page"), "?"))
        if doi_raw and doi_raw.lower() != "sin doi":
            foot_pills.append(
                f'<a class="pill" href="https://doi.org/{E(doi_raw)}" target="_blank" rel="noopener noreferrer">'
                f"{psi} · DOI: {E(doi_raw)} · Pág. {page_str}</a>"
            )
        else:
            foot_pills.append(f'<span class="pill">{psi} · DOI: sin DOI · Pág. {page_str}</span>')
    foot = "".join(foot_pills) or '<span class="pill muted">Sin fuente directa en PSI</span>'
    expl_html = (
        f'<div class="meta-line" style="margin-top:-4px;margin-bottom:10px">{E(it["explanation"])}</div>'
        if it.get("explanation")
        else ""
    )
    scope_meta = ""
    if it.get("scope") or it.get("psi_ids"):
        scope_es = ui.scope_label(it.get("scope", ""))
        parts = [p for p in [scope_es, ", ".join(it.get("psi_ids", []))] if p]
        scope_meta = f'<div class="meta-line">{" · ".join(E(p) for p in parts)}</div>'

    has_cites_cls = " has-cites" if it["cites"] else ""
    st.markdown(
        f'<div class="card find {it["st"]}{has_cites_cls}">'
        f'<div class="h"><div>{scope_meta}<h3>{E(it["title"])}</h3></div>{ui.badge(it["lab"], it["kb"])}</div>'
        f'<p>{it["text"]}</p>{expl_html}{foot}</div>',
        unsafe_allow_html=True,
    )
    if it["cites"]:
        with st.container(key=f"ins_cite_{idx}"):
            st.markdown(
                f"<style>.st-key-ins_cite_{idx}{{margin-top:-15px;margin-bottom:14px}}"
                f".st-key-ins_cite_{idx} [data-testid='stExpander'] details{{"
                f"border-top-left-radius:0!important;border-top-right-radius:0!important;"
                f"border-top:1px dashed #E2E8F0!important;background:#FAFBFD!important;"
                f"border-left:4px solid {'#15803D' if it['st']=='' else '#1D4ED8' if it['st']=='b' else '#D97706'}!important}}"
                f"</style>",
                unsafe_allow_html=True,
            )
            with st.expander("Ver cita textual del reporte"):
                for c in it["cites"]:
                    q_txt = ui.clean_str(c.get("quote") or c.get("text"), "(sin cita textual)")
                    st.markdown(f"> {E(q_txt)}  \n{ui.cite_md(c)}")
