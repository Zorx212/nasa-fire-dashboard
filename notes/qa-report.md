# Reporte de QA de Frontend (`uri/frontend`)

## 1. Suite automatizada (`tests/test_frontend_qa.py`)
Ejecutada después de la última edición con `.venv/bin/python -m unittest discover -s tests -v`:
- **Resultado:** `Ran 12 tests in 1.102s — OK` (`0` fallos, `0` errores, `0` omitidos).
- **Alcance:** Todos los tests de rutas usan el conjunto de ejemplo (`data/mock`) y pruebas sintéticas para formatos `schemas.py` (`InsightsDocument`) y `NaN` en `Comparación`.
- **Cobertura verificada:**
  1. `test_brand_logo_assets_and_safe_inline_svg`: assets en `app/assets/` existentes e isotipo SVG con `.ff-orb` y caja simétrica sin estilos/metadatos inline.
  2. `test_extract_and_norm_insights_both_formats`: compatibilidad con lista mock (`claims`/`note`) y diccionario `InsightsDocument` (`src/insights/schemas.py`).
  3. `test_num_and_clean_str_never_render_nan_or_orphan_unit`: valores `NaN` devuelven `'—'` sin texto `'nan'` ni unidad huérfana.
  4. `test_outcome_counts_negation_and_bilingual`: `'no propagó'` no cuenta como propagación; soporte ES/EN.
  5. `test_scope_and_domain_labels_translate_to_spanish`: traducción de alcances, materiales y resultados al español.
  6. `test_all_five_routes_render_without_exception`: ejecución sin excepciones de `app.py`, `1_Ranking.py`, `2_Comparacion.py`, `3_Insights.py` y `4_Cobertura.py`.
  7. `test_cobertura_gap_hero_and_fillpattern_and_scenario_spin`: `4_Cobertura.py` renderiza `.gap-hero` (`56px`) + `fillpattern` diagonal rojo en zona vacía; `1_Ranking.py` alterna `spin-a`/`spin-b` y `cnt-a`/`cnt-b` en los 3 escenarios.
  8. `test_comparacion_handles_nan_spread_and_renders_charts_without_zero_fallback`: gráficas presentes en `2_Comparacion.py` y `NaN` anotados como `'sin dato'`.
  9. `test_insights_schemas_format_two_citations_and_insufficient_data`: formato `schemas.py` con 2 citas, superíndices y enlace a Cobertura bajo `insufficient_data`.
  10. `test_insights_unanswered_question_and_translated_scopes`: `3_Insights.py` usa cero `st.expander` en el cuerpo principal (`len(at.main.expander) == 0`), rinde `<details class="cite-det">`, traduce alcances y avisa cuando no hay respuesta.
  11. `test_multipage_navigation_preserves_sidebar_state`: estado de escenario y filtros preservado al navegar desde `app.py`.
  12. `test_ranking_scenario_fallback_and_toggle`: en `1_Ranking.py`, `'Traje Espacial'` muestra fallback de 10 cercanos con `'0 exactos'` y segundo clic desactiva el escenario.

## 2. Auditoría en navegador real (Headless Chrome CDP)
Playwright no está instalado en `.venv`; la verificación en navegador se ejecutó directamente mediante Chrome Headless + protocolo CDP (`verify_viewports.py` y auditoría de frames de transición) contra Streamlit real:
- **Rutas y HTTP:** `/`, `/Ranking`, `/Comparacion`, `/Insights`, `/Cobertura` respondieron `HTTP 200` y `0` `stException`.
- **Viewports `1440×900` y `390×844`:** `scrollWidth == clientWidth` (`1440 == 1440` y `390 == 390`) en las 5 rutas, `0` círculos nativos visibles en `st.radio` de `3_Insights.py`, pestaña superior alineada (`topDiff: 0`, `hDiff: 0`) e isotipo `44×44` con `favicon`.
- **Transición sin cortes (`TAB TRANSITION AUDIT` y `ORBIT BOOST AUDIT`):**
  - Capturas cuadro a cuadro (`15ms`, `45ms`, `85ms`, `140ms`, `220ms`) tras clic real de ratón de `/Ranking` a `/Comparacion`: `liveTop: 20 == shTop: 20` (`0px` de salto vertical), contadores `.cnt` estables en su valor final (`10 ensayos`, `80 % propagó`) sin reinicio a `0`, ancho completo conservado en `#ff-shield-host`, y `waiting: true` mantenido hasta que `liveTab === "Comparación"` y los 12 `.main-svg` de Plotly están montados antes de iniciar el cross-dissolve.
  - Reloj SMIL del isotipo al pulsar escenario (`ORBIT BOOST AUDIT`, 61 frames): `startT: 2.048 -> midT: 8.09 -> endT: 12.036` (`deltaT: 9.99`, `monotonic: true`), sin reinicio a `0` ni salto cuando React actualiza el DOM.
  - Bajo `prefers-reduced-motion: reduce`, `animationDuration = 1e-05s`.
- **Tipografía y reglas visuales (`CSS/NAV AUDIT`, 25 frames entre `/Ranking` e `Insights`):**
  - `lostGrid: false`, `lostCss: false`, `flashedNav: false`.
  - Fuentes activas confirmadas con `document.fonts.check`: `fontsCond: true` (`Barlow Semi Condensed`), `fontsInter: true` (`Inter`), `fontsMono: true` (`JetBrains Mono`).
  - Toggle `<details class="cite-det">`: `detBefore: false`, `detAfter: true`.
  - Auditoría de geometría y sombras (`badRadius: []`, `badShadow: []`): cero radios `> 4px` y cero `box-shadow`.

## 3. Nota de ámbito
- No se modificaron `app/app.py`, `app/data_loader.py`, `src/**`, `data/**` ni `requirements.txt`.
- No existe `eval/check_against_verification.py` ni `data/reports` en el repositorio actual.
