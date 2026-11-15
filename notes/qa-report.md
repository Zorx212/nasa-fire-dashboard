# Reporte de QA y Animaciones de Frontend · Flame in Freefall

## 1. Errores corregidos (causa → solución)

1. **Círculos de radio visibles en controles horizontales (`app/ui.py`):**
   - **Causa:** En Streamlit 1.67, `st.radio(..., horizontal=True)` estructura el DOM como `[data-testid="stRadioGroup"][data-orientation="horizontal"] > div > label[data-testid="stRadioOption"]`, donde el icono circular es `> div > div:not([data-testid="stMarkdownContainer"])`. El selector previo (`div[role="radiogroup"] > label > div:first-child`) no coincidía con esa jerarquía.
   - **Solución:** Se actualizaron los selectores al DOM real de Streamlit 1.67 (`radioCirclesVisible = 0` verificado por CDP en las 5 rutas).
2. **Estilo de botones de escenario en sidebar no aplicado (`app/ui.py`):**
   - **Causa:** Al incluir `help=...` en `st.button`, Streamlit envuelve `<button data-testid="stBaseButton-secondary">` dentro de `span[data-testid="stTooltipHoverTarget"]`, rompiendo el combinador de hijo directo `.stButton > button`.
   - **Solución:** Se reemplazó por selectores descendientes `section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]` (`#EEF1F5`) y `[data-testid="stBaseButton-primary"]` (`#E84C22`).
3. **Pestañas superiores desalineadas y apiladas en móvil (`app/ui.py`):**
   - **Causa:** `div.tab` y `st.page_link` tenían alturas/márgenes distintos y en `≤700px` las columnas pasaban a `flex-basis: 100%`, ocupando ~250 px verticales.
   - **Solución:** Se envolvió la barra en `st.container(key="top_nav")`, se igualó `height`/`min-height`/`padding` entre `.tab` y `[data-testid="stPageLink-NavLink"]`, y en `≤700px` se mantuvo en una sola fila horizontal compacta (`32px` de alto).
4. **Superposición de título/leyenda y recorte de anotación en Cobertura móvil (`app/pages/4_Cobertura.py`):**
   - **Causa:** La leyenda superior derecha colisionaba con el título en `390px`, la anotación de `Traje Espacial` centrada en `x=95` se cortaba a la derecha y `ISS / Tierra` tenía baja opacidad.
   - **Solución:** Se movió la leyenda debajo del eje X (`y=-0.18`, sin título), se ancló `Traje Espacial` con `x=99, xanchor="right"`, y `ISS / Tierra` con `x=24.5, xanchor="left"` y mayor contraste.
5. **Toast de arranque sobre contenido (`app/ui.py`):**
   - **Causa:** Posicionado en `bottom: 18px; right: 22px`, cubría parte de la tabla o matriz.
   - **Solución:** Se reubicó arriba a la derecha (`top: 12px; right: 16px; pointer-events: none; 1.6s`), mostrándose solo una vez por sesión.
6. **Repetición de animaciones en cada rerun de controles (`app/ui.py`):**
   - **Causa:** Cada cambio de slider/radio re-ejecuta el script y volvía a disparar `fadeInUp` y `growBar`.
   - **Solución:** `ui.setup(title)` compara `st.session_state.get("_last_page") != title` y en reruns de la misma vista inyecta `animation: none !important` sobre los contenedores y filas.
7. **Uso de `importlib.reload(ui)` en las páginas (`app/app.py`, `app/pages/*.py`):**
   - **Causa:** Parche temporal para recargar `ui.py` en caliente.
   - **Solución:** Se eliminó de las 5 páginas y se verificó todo sobre un servidor limpio en el puerto `8511`.
8. **Etiquetas de alcance en inglés y expander separado en Insights (`app/pages/3_Insights.py`, `app/ui.py`):**
   - **Causa:** `scope` (`experiment`, `comparison`) se mostraba crudo y el `st.expander` tenía margen separado respecto a `.card.find`.
   - **Solución:** Se tradujo solo en presentación con `ui.scope_label()` y se acopló el contenedor del expander al pie de la tarjeta con el mismo borde izquierdo semántico.
9. **Botón «Deploy» visible y espacio vacío superior en sidebar (`.streamlit/config.toml`, `app/ui.py`):**
   - **Causa:** Toolbar por defecto y `stLogoSpacer` + `stSidebarHeader` de 60 px en el sidebar.
   - **Solución:** Se configuró `[client] toolbarMode = "minimal"` en `.streamlit/config.toml` y se ocultó `stLogoSpacer` reduciendo el padding superior del sidebar.
10. **Falta de gráficas comparativas en Comparación (`app/pages/2_Comparacion.py`):**
    - **Causa:** Se habían retirado las gráficas previas sin sustituirlas por gráficas con escalas separadas.
    - **Solución:** Se añadieron 2 bloques de gráficas: *Condiciones de prueba* (3 *small multiples* con ejes y unidades independientes para `O₂ (%)`, `Presión (kPa)` y `Flujo (cm/s)`) y *Comportamiento de llama* (`flame_spread_rate` coloreado por resultado), anotando valores `NaN` como `"sin dato"` y nunca como `0`.

## 2. Animaciones y transiciones implementadas

- **Accesibilidad (`prefers-reduced-motion`):** Todas las animaciones viven dentro de `@media (prefers-reduced-motion: no-preference)` y se reducen a `0.01ms` en `@media (prefers-reduced-motion: reduce)`.
- **Tarjetas KPI escalonadas:** `animation-delay` incremental (`0ms`, `55ms`, `110ms`, `165ms`) en `[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(n) .card.kpi`.
- **Tabla de ranking:** aparición escalonada corta (`15ms` a `150ms`) y llenado de barras `.score-track i` con `transform: scaleX` (sin reflow).
- **Pestaña activa y botón de escenario activo:** subrayado `#E84C22` en pestaña activa y pulso único (`scenPulse`, 1 iteración) en el escenario seleccionado.
- **Tarjetas de Insights y banner de Cobertura:** trazado vertical del borde izquierdo (`::before` con `scaleY`) y pulso único de entrada en `.ban`.
- **Plotly y Expanders:** `transition=dict(duration=300, easing="cubic-in-out")`, `hoverlabel` estilizado y transición suave en `<details>`.

## 3. Comandos y resultados de verificación

```bash
cd /Users/palaciosu/Downloads/nasa-fire-dashboard-main
.venv/bin/python -m compileall -q app tests
.venv/bin/python -m unittest discover -s tests -v
```

- **Tests unitarios e integración (`tests/test_frontend_qa.py`):** `9/9 OK` en `0.88s`.
- **Verificación HTTP y visual con Chrome Headless CDP (puerto `8511`):**
  - Smoke HTTP en `/`, `/Ranking`, `/Comparacion`, `/Insights`, `/Cobertura` → `HTTP 200` en las 5 rutas.
  - Viewport `1440×900` (5 rutas): `stException = 0`, `scrollWidth == clientWidth == 1440`, `radioCirclesVisible = 0`, `secBtnBg = rgb(238, 241, 245)`.
  - Viewport `390×844` (5 rutas): `stException = 0`, `scrollWidth == clientWidth == 390`, `radioCirclesVisible = 0`, `secBtnBg = rgb(238, 241, 245)`.
  - Emulación `prefers-reduced-motion: reduce`: `animationDuration = 1e-05s` (`0.01ms`).

## 4. Confirmación de archivos protegidos

No se modificó ni reformateó ningún archivo de backend, contrato o datos (`app/data_loader.py`, `src/**`, `data/**`, `requirements.txt`, `work/pre-ui-integration/**`).
