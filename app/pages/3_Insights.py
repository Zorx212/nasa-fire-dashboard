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
    st.caption(f"Modelo de extracción fuera de línea: `{meta['model']}` · versión de prompt {meta.get('prompt_version', '1.0')}")

q_search = st.text_input("Buscar en hallazgos", placeholder="Filtrar por material, condición o estudio PSI...")

questions = [
    "Todas las respuestas precalculadas",
    "¿Qué cambia al subir O₂ a ≥30%?",
    "¿Qué materiales sólidos propagan más rápido?",
    "¿Qué sabemos de gravedad parcial?",
]
question = st.radio("Preguntas sugeridas", questions, horizontal=True)

items = [ui.norm(i) for i in insights_list]
if q_search.strip():
    q_low = q_search.strip().lower()
    items = [
        item
        for item in items
        if q_low in (item["title"] + " " + item["text"] + " " + item.get("explanation", "") + " " + " ".join(item.get("psi_ids", []))).lower()
    ]

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

visible_items = [it for it in items if scope == "todos" or it["scope"] == scope]

for k, it in enumerate(visible_items, 1):
    cite_pids = {ui.clean_str(c.get("psi_id"), "") for c in it["cites"] if ui.clean_str(c.get("psi_id"), "")}
    hi_df = df[df["psi_id"].astype(str).isin(cite_pids)] if (cite_pids and "psi_id" in df.columns) else df.iloc[0:0]

    expl_html = (
        f'<div class="ins-expl">{E(it["explanation"])}</div>'
        if it.get("explanation")
        else ""
    )

    fn_rows = []
    for n_cite, c in enumerate(it["cites"], 1):
        psi = E(ui.clean_str(c.get("psi_id"), "?"))
        doi_raw = ui.clean_str(c.get("doi"), "")
        page_str = E(ui.clean_str(c.get("page"), "?"))
        has_doi = bool(doi_raw and doi_raw.lower() not in ("sin doi", "doi pendiente"))
        doi_meta = f"DOI {E(doi_raw)}" if has_doi else "DOI pendiente"
        doi_link = (
            f' <a class="doi-open" href="https://doi.org/{E(doi_raw)}" target="_blank" rel="noopener noreferrer">Abrir DOI</a>'
            if has_doi
            else ""
        )
        has_q = bool(c.get("has_quote"))
        if has_q:
            q_body = f'{E(ui.clean_str(c.get("quote"), ""))}{doi_link}'
        else:
            q_txt = ui.clean_str(c.get("claim_text") or c.get("text"), "Sin texto disponible.")
            q_body = f'{E(q_txt)} <span class="cite-noq">— Este formato no incluye cita textual</span>{doi_link}'
        fn_rows.append(
            f'<details class="cite-det"><summary class="cite-sum">'
            f'<span class="cite-num">{n_cite}</span>'
            f'<span class="cite-ref">{psi} · {doi_meta} · p. {page_str}</span>'
            f'<span class="cite-toggle"></span>'
            f'</summary><div class="cite-q">{q_body}</div></details>'
        )
    fn_html = f'<div class="fn-list">{"".join(fn_rows)}</div>' if fn_rows else ""

    loc_svg = ui.locator(df, hi_df)
    body_html = (
        f'<div class="ins-hdr">'
        f'<h3 class="ins-title">{E(it["title"])}</h3>'
        f'<div class="ev-status">{ui.ev_meter(it["st"])}<span class="ev-lab">{E(it["lab"])}</span></div>'
        f'</div>'
        f'<div class="f-split"><div class="f-main"><p class="ins-p">{it["text"]}</p>{expl_html}</div>'
        f'<div class="f-loc">{loc_svg}</div></div>'
        f'{fn_html}'
    )
    st.markdown(ui.ficha(f"Insight {k} · {len(hi_df)} ensayos citados", body_html), unsafe_allow_html=True)

    if it["st"] == "w":
        st.markdown(
            '<div style="font-size:12.5px;color:#64748B;margin:-4px 0 4px 0">No hay ensayos que respondan esto. Revisa la cobertura.</div>',
            unsafe_allow_html=True,
        )
        try:
            st.page_link("pages/4_Cobertura.py", label="Ver cobertura")
        except Exception:
            st.markdown(
                '<a href="/Cobertura" style="font-size:13px;font-weight:600;color:#E84C22;text-decoration:none">Ver cobertura</a>',
                unsafe_allow_html=True,
            )
