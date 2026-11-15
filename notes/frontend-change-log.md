# Cambios de frontend · Flame in Freefall (vs. `main` en GitHub)

## Alcance y compatibilidad con `main`

- **Base comparada:** Último estado de `main` en GitHub (que incluye el esqueleto inicial de `app/` y los avances de backend en `data/catalog.csv`, `src/llm/cache.py` y `tests/test_cache.py`).
- **Archivos incluidos en este PR:** únicamente archivos de frontend y documentación QA (`.streamlit/config.toml`, `app/ui.py`, `app/app.py`, `app/pages/1_Ranking.py`, `app/pages/2_Comparacion.py`, `app/pages/3_Insights.py`, `app/pages/4_Cobertura.py`, `tests/test_frontend_qa.py`, `notes/frontend-change-log.md`, `notes/qa-report.md`).
- **Cero conflictos con backend:** No se modificaron `app/data_loader.py`, `src/**`, `data/**` ni `requirements.txt`.

## Resumen de cambios desde `main`

### 1. Sistema de diseño e infraestructura visual (`app/ui.py` y `.streamlit/config.toml`)
- **Tema y configuración (`.streamlit/config.toml`):** Tema claro cálido (`#F7F8FA`, primario `#E84C22`, texto `#0F172A`, tipografía `Space Grotesk` / `IBM Plex Sans` / `JetBrains Mono`) y `toolbarMode = "minimal"` para ocultar el botón «Deploy» manteniendo el botón `>>` del sidebar en móvil.
- **Shell compartido (`ui.setup`, `ui.header`, `ui.tabs`, `ui.sidebar`):**
  - Header superior con identidad **Flame in Freefall**, subtítulo técnico y pill contextual **Modo Demo** cuando `using_mock=True`.
  - Navegación superior (`st.container(key="top_nav")`) con 5 pestañas (`Inicio`, `Ranking`, `Comparación`, `Insights`, `Cobertura`), altura uniforme (`36px` desktop / `32px` móvil) y fila horizontal sin apilamiento en pantallas `≤700px`.
  - Sidebar unificado con filtros persistentes entre páginas (`_saved_filters`), selector segmentado de material dinámico según los valores presentes en el CSV, sliders de `O₂ (%)`, `Presión (kPa)` y `Flujo (cm/s)` con inclusión de filas `NaN`, presets de escenario (`ISS / Tierra`, `Base Lunar / Rover`, `Traje Espacial`) marcados como supuestos pendientes de validar, y sliders de pesos del ranking.
- **Selectores CSS adaptados a Streamlit 1.67:**
  - Controles `st.radio` horizontales estilizados como control segmentado tipo píldora ocultando el círculo nativo (`[data-testid="stRadioGroup"][data-orientation="horizontal"]`).
  - Botones de escenario en sidebar estilizados mediante selectores descendientes compatibles con wrappers de tooltip (`[data-testid="stBaseButton-secondary"]` y `[data-testid="stBaseButton-primary"]`).
  - Compactación del encabezado del sidebar (`[data-testid="stSidebarHeader"]`, `[data-testid="stLogoSpacer"]`).
- **Animaciones y accesibilidad:**
  - Detección de cambio de página (`_last_page != title`) para ejecutar animaciones de entrada solo al navegar a una vista nueva y desactivarlas (`animation: none !important`) al mover filtros/sliders.
  - Respeto estricto a `@media (prefers-reduced-motion: reduce)` y transiciones suaves en gráficas Plotly (`300ms cubic-in-out`).
  - Toast de bienvenida no bloqueante (`pointer-events: none`) ubicado en la esquina superior derecha y mostrado una sola vez por sesión (`_boot_shown`).

### 2. Pantallas del dashboard (`app/app.py` y `app/pages/1..4`)
- **Inicio (`app/app.py`):** Tarjetas KPI (`Experimentos`, `Investigaciones PSI`, `Insights con cita`, `Rango de O₂`) compatibles con lista plana o `InsightsDocument`, y tarjetas de acceso rápido a los 4 módulos.
- **1 · Ranking (`app/pages/1_Ranking.py`):**
  - Tarjetas KPI con conteo dinámico de resultados (`propagó`, `se extinguió`, `marginal`), tabla HTML con barras de `score_total`, pills semánticos y enlaces DOI.
  - Fallback explícito (`"0 exactos — mostrando tabla completa"`) cuando un filtro o escenario no tiene coincidencias exactas.
  - Panel de inspección rápida por experimento con gráfica horizontal apilada del desglose de puntaje (`Relevancia`, `Riesgo`, `Evidencia`, `Cobertura`) y leyenda HTML alineada.
- **2 · Comparación (`app/pages/2_Comparacion.py`):**
  - Selector de 2 o 3 experimentos lado a lado con detección automática de diferencias entre filas (`⚡ Difiere`), enlace DOI en la cabecera de cada tarjeta y manejo seguro de `NaN` (`—` / `sin dato`, sin unidades huérfanas).
  - **2 secciones de gráficas comparativas debajo de la matriz:**
    1. *Condiciones de prueba (Small Multiples):* 3 gráficas independientes (`Oxígeno (%)`, `Presión (kPa)`, `Flujo (cm/s)`) sin mezclar unidades en un mismo eje y anotando `NaN` como `"sin dato"` (nunca como `0`).
    2. *Comportamiento de llama:* gráfica de `flame_spread_rate` coloreada por resultado y con verificación de unidad compatible (`spread_rate_unit`).
- **3 · Insights (`app/pages/3_Insights.py`):**
  - Modo honesto de insights precalculados (sin simular chat LLM en vivo), compatible tanto con `insights_mock.json` como con `InsightsDocument` (`src/llm/schemas.py`).
  - Filtro de alcance traducido en interfaz (`Todos`, `Experimento`, `Comparación`), tarjetas semánticas según nivel de confianza (`alta`, `media`, `baja`) con citas `PSI + DOI + pág.` y expander de cita textual integrado visualmente a cada tarjeta.
- **4 · Cobertura (`app/pages/4_Cobertura.py`):**
  - Tarjetas resumen (`Celdas con datos`, `Vacíos (0 exp.)`, `Cobertura %`) y pestañas para *Mapa de Cobertura* (scatter `O₂` vs `Presión` con las 3 zonas de referencia `ISS / Tierra`, `Base Lunar / Rover`, `Traje Espacial`, tooltips agrupados para coordenadas repetidas y leyenda inferior apta para móvil) y *Matriz de Vacíos* (heatmap con celdas vacías destacadas).

### 3. Pruebas automatizadas (`tests/test_frontend_qa.py`)
- Suite de 9 pruebas automatizadas (`unittest` + `streamlit.testing.v1.AppTest`) que validan helpers numéricos, conteo de resultados, ambos esquemas de `insights`, traducción de alcances, ausencia de `NaN` graficados como `0`, desactivación de animaciones en reruns y renderizado sin excepciones de todas las páginas.
