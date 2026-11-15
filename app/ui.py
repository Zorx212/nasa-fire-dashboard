"""Capa visual (solo frontend): CSS, componentes HTML ("fichas de ensayo") y sidebar compartido.
No toca datos ni ranking: todo sale de data_loader."""
import re
from html import escape as E
from pathlib import Path

import pandas as pd
import streamlit as st

import data_loader as _dl
from data_loader import DEFAULT_WEIGHTS

ASSETS = Path(__file__).parent / "assets"

MAT_LABELS = {  # solo presentación: el valor original de material_type no se modifica
    "gas": "Gas",
    "solid": "Sólido",
    "sólido": "Sólido",
    "solido": "Sólido",
    "liquid": "Líquido",
    "líquido": "Líquido",
    "liquido": "Líquido",
}
OUTCOME_LABELS = {  # solo presentación: kind() sigue usando el texto original
    "self_extinguished": "Se autoextinguió",
    "extinguished": "Se extinguió",
    "flow_terminated": "Flujo detenido",
    "propagated": "Propagó",
    "sustained": "Llama sostenida",
    "no_ignition": "Sin ignición",
}
SCEN = {  # zonas objetivo: o2 (%), presion (kPa) — supuestos del equipo pendientes de validar
    "Base Lunar / Rover": {"o2": (30, 60), "p": (0, 70.3), "desc": "O₂ 30–60 % · hasta 70.3 kPa"},
    "Traje Espacial": {"o2": (90, 100), "p": (0, 35), "desc": "O₂ 90–100 % · hasta 35 kPa"},
    "ISS / Tierra": {"o2": (19, 23), "p": (95, 102), "desc": "O₂ 19–23 % · 95–102 kPa"},
}
COMP = {
    "relevancia": "#E84C22",
    "riesgo": "#B91C1C",
    "evidencia": "#0F766E",
    "cobertura": "#64748B",
}
COMP_LABELS = {
    "relevancia": "Relevancia Luna/Marte",
    "riesgo": "Riesgo de propagación",
    "evidencia": "Calidad de evidencia",
    "cobertura": "Cobertura",
}
SCOPE_LABELS = {
    "todos": "Todos",
    "experiment": "Experimento",
    "comparison": "Comparación",
    "global": "Global",
}
TABS = [
    ("Ranking", "pages/1_Ranking.py"),
    ("Comparación", "pages/2_Comparacion.py"),
    ("Insights", "pages/3_Insights.py"),
    ("Cobertura y vacíos", "pages/4_Cobertura.py"),
]

_FALLBACK_LOGO_SVG = (
    '<svg width="44" height="44" viewBox="0 0 64 64" fill="none" role="img" aria-label="Flame in Freefall">'
    '<g transform="rotate(-24 32 32)" fill="none" stroke-linecap="round">'
    '<g class="ff-orb"><rect x="-4" y="-4" width="72" height="72" fill="transparent" stroke="none" pointer-events="none"/>'
    '<path d="M59 32 A27 10 0 0 0 5 32" stroke="#0F172A" stroke-opacity=".35" stroke-width="1.6"/>'
    '<circle cx="50.5" cy="41" r="2.5" fill="#0F172A" opacity=".35"/></g>'
    '<g class="ff-sp"><circle cx="32" cy="32" r="15" fill="#E84C22"/>'
    '<path class="ff-fl" d="M33.5 20 C33.5 25 40 28 40 35.5 A8 8 0 0 1 24 35.5 C24 30.5 27 28.5 29 24.5 C29.8 27 31 27.6 31.6 26.4 C32.4 24.5 32 22 33.5 20Z" fill="#fff"/></g>'
    '<g class="ff-orb"><rect x="-4" y="-4" width="72" height="72" fill="transparent" stroke="none" pointer-events="none"/>'
    '<path d="M5 32 A27 10 0 0 0 59 32" stroke="#0F172A" stroke-width="1.6"/>'
    '<circle cx="50.5" cy="41" r="2.5" fill="#0F172A"/></g></g></svg>'
)


def _load_logo_svg(size=44):
    """Carga el isotipo SVG animado desde app/assets/ sin <style>/<metadata> inline.
    Separa los anillos de órbita en grupos <g class="ff-orb"> con caja simétrica en (32,32)
    para que giren 0->360° sin desplazamiento del centro ni salto al terminar."""
    p = ASSETS / "logo_animated.svg"
    if not p.exists():
        return _FALLBACK_LOGO_SVG.replace('width="44" height="44"', f'width="{size}" height="{size}"', 1)
    raw = p.read_text(encoding="utf-8")
    raw = re.sub(r"<style>.*?</style>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"<metadata>.*?</metadata>", "", raw, flags=re.DOTALL)
    raw = raw.replace(' xmlns:c2pa="http://c2pa.org/manifest"', "").replace("\n", "")
    raw = raw.replace('width="64" height="64"', f'width="{size}" height="{size}"', 1)

    m = re.search(
        r'(<g transform="rotate\(-24 32 32\)"[^>]*>)(.*?)(<g class="ff-sp">.*?</g>)(.*?)(</g></svg>)$',
        raw,
    )
    if not m:
        return raw.replace('<g transform="rotate(-24 32 32)"', '<g class="ff-orb" transform="rotate(-24 32 32)"', 1)

    open_g, back_ring, center_flame, front_ring, close_g = m.groups()
    sym_box = '<rect x="-4" y="-4" width="72" height="72" fill="transparent" stroke="none" pointer-events="none"/>'
    return (
        raw[: m.start()]
        + f'{open_g}<g class="ff-orb">{sym_box}{back_ring}</g>'
        + center_flame
        + f'<g class="ff-orb">{sym_box}{front_ring}</g>{close_g}'
    )


LOGO = _load_logo_svg(44)
LOGO_SVG = LOGO
LOGO_HERO_SVG = _load_logo_svg(56)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

@property --n {
  syntax: '<integer>';
  inherits: false;
  initial-value: 0;
}

:root {
  --ink: #0F172A;
  --paper: #F6F7F9;
  --white: #FFFFFF;
  --line: #DDE2E8;
  --gray: #64748B;
  --flame: #E84C22;
  --red: #B91C1C;
  --teal: #0F766E;
  --blue: #1D4ED8;
  --font-cond: "Barlow Semi Condensed", "Arial Narrow", system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace;
}

@keyframes ff-k {
  0%, 100% { transform: scale(1, 1); }
  40% { transform: scale(0.96, 1.07); }
  70% { transform: scale(1.03, 0.97); }
}
@keyframes ff-b {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.035); }
}
@keyframes ff-once-a {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.035); }
}
@keyframes ff-once-b {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.035); }
}
@keyframes ff-count {
  from { --n: 0; }
}
@keyframes ff-count-a {
  from { --n: 0; }
}
@keyframes ff-count-b {
  from { --n: 0; }
}
@keyframes ff-tab-in {
  from { opacity: 0; transform: translate3d(0, 4px, 0); }
  to { opacity: 1; transform: translate3d(0, 0, 0); }
}

html {
  interpolate-size: allow-keywords;
}

html, body, .stApp, [class*="css"] {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-size: 13px;
  color: var(--ink);
}

html, [data-testid="stAppViewContainer"] {
  scrollbar-gutter: stable;
}

html.ff-waiting #root [data-testid="stMainBlockContainer"] {
  opacity: 0 !important;
  pointer-events: none !important;
}

#ff-shield-host {
  position: fixed !important;
  inset: 0 !important;
  pointer-events: none !important;
  z-index: 999980 !important;
  overflow: hidden !important;
  background: transparent !important;
  background-image: none !important;
}
#ff-shield-host *,
#ff-shield-host *::before,
#ff-shield-host *::after {
  animation: none !important;
  transition: none !important;
}

/* Lienzo milimétrico cuadriculado 24 px / 120 px */
.stApp {
  background-color: var(--paper) !important;
  background-image:
    linear-gradient(rgba(15, 23, 42, .085) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, .085) 1px, transparent 1px),
    linear-gradient(rgba(15, 23, 42, .04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, .04) 1px, transparent 1px) !important;
  background-size: 120px 120px, 120px 120px, 24px 24px, 24px 24px !important;
}

[data-stale="true"] {
  opacity: 1 !important;
  transition: opacity 140ms ease !important;
}

h1, h2, h3, .card h3, .card > b {
  font-family: var(--font-cond) !important;
  color: var(--ink);
  letter-spacing: -0.01em;
}
h1 {
  font-size: 32px !important;
  font-weight: 600 !important;
  line-height: 1.1 !important;
}
h2, h3, .card h3, .card > b {
  font-size: 17px !important;
  font-weight: 600 !important;
  line-height: 1.25 !important;
  margin: 0;
}

[data-testid="stSidebarNav"] { display: none !important; }
header[data-testid="stHeader"] {
  background: transparent !important;
  height: 2.5rem !important;
  min-height: 2.5rem !important;
}

/* Colapsar por completo contenedores que inyectan únicamente etiquetas style o script (sin brecha flex ni colapsar SVG/logos) */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style):not(:has(svg)):not(:has(.brand)),
[data-testid="stElementContainer"]:has(.ff-boot):not(:has(svg)):not(:has(.brand)) {
  display: none !important;
}

[data-testid="stSkeleton"] {
  opacity: 0 !important;
  animation: none !important;
}

.block-container {
  padding: 1.5rem clamp(1rem, 2.4vw, 2.2rem) 2.5rem !important;
  max-width: 1440px !important;
}

/* Sidebar blanco liso con borde derecho de 1 px, sin cuadrícula */
section[data-testid="stSidebar"] {
  background: var(--white) !important;
  background-image: none !important;
  border-right: 1px solid var(--line) !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
  height: auto !important;
  min-height: 24px !important;
  padding: 6px 10px 0 10px !important;
  margin-bottom: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stLogoSpacer"] {
  display: none !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
  padding-top: 0.2rem !important;
  padding-bottom: 1.2rem !important;
}

.sec-hdr {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray);
  margin: 12px 0 4px 0;
}

/* Botones de escenario en sidebar (radio <= 4 px, sin sombra) */
section[data-testid="stSidebar"] [data-testid^="stBaseButton-"] {
  border-radius: 4px !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  min-height: 36px !important;
  padding: 0.4rem 0.75rem !important;
  box-shadow: none !important;
  transition: background-color 150ms cubic-bezier(0.22, 1, 0.36, 1), color 150ms cubic-bezier(0.22, 1, 0.36, 1), border-color 150ms cubic-bezier(0.22, 1, 0.36, 1) !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] [data-testid^="stBaseButton-"][data-ff-opt="off"] {
  background-color: var(--white) !important;
  color: var(--ink) !important;
  border: 1px solid var(--line) !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid^="stBaseButton-"][data-ff-opt="off"] p {
  color: var(--ink) !important;
  font-weight: 500 !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
section[data-testid="stSidebar"] [data-testid^="stBaseButton-"][data-ff-opt="on"] {
  background-color: var(--flame) !important;
  color: var(--white) !important;
  border: 1px solid var(--flame) !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p,
section[data-testid="stSidebar"] [data-testid^="stBaseButton-"][data-ff-opt="on"] p {
  color: var(--white) !important;
  font-weight: 600 !important;
}

/* Controles nativos con radio <= 4 px y sin sombras */
[data-baseweb="input"] > div,
[data-baseweb="select"] > div {
  border-radius: 4px !important;
  box-shadow: none !important;
  transition: border-color 140ms ease !important;
}

/* Radio horizontal tipo Segmented Control (sin círculos nativos) */
[data-testid="stRadioGroup"][data-orientation="horizontal"] {
  background: var(--white) !important;
  border: 1px solid var(--line) !important;
  padding: 3px !important;
  border-radius: 4px !important;
  gap: 3px !important;
  display: inline-flex !important;
  flex-wrap: wrap !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stRadioGroup"][data-orientation="horizontal"] {
  display: flex !important;
  width: 100% !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] > div {
  flex: 1 1 auto !important;
  display: flex !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"] {
  flex: 1 1 auto !important;
  justify-content: center !important;
  align-items: center !important;
  margin: 0 !important;
  padding: 5px 10px !important;
  border-radius: 3px !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  cursor: pointer !important;
  box-shadow: none !important;
  transition: background-color 150ms cubic-bezier(0.22, 1, 0.36, 1), border-color 150ms cubic-bezier(0.22, 1, 0.36, 1) !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {
  display: none !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p {
  font-size: 13px !important;
  font-weight: 500 !important;
  color: var(--gray) !important;
  margin: 0 !important;
  text-align: center !important;
  transition: color 150ms ease !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"][data-selected="true"],
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"]:has(input:checked),
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"][data-ff-opt="on"] {
  background: var(--paper) !important;
  border: 1px solid var(--line) !important;
  box-shadow: none !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"][data-ff-opt="off"] {
  background: transparent !important;
  border: 1px solid transparent !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"][data-selected="true"] [data-testid="stMarkdownContainer"] p,
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"]:has(input:checked) [data-testid="stMarkdownContainer"] p,
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"][data-ff-opt="on"] [data-testid="stMarkdownContainer"] p {
  color: var(--ink) !important;
  font-weight: 600 !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"][data-ff-opt="off"] [data-testid="stMarkdownContainer"] p {
  color: var(--gray) !important;
  font-weight: 500 !important;
}

.mono, .n {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* Ficha de ensayo (.f) con marcas de registro en las 4 esquinas y pestaña .tag */
.f,
.st-key-cov_map_ficha {
  position: relative;
  background: var(--white) !important;
  border: 1px solid var(--line) !important;
  padding: 26px 24px 18px !important;
  margin-top: 26px !important;
  margin-bottom: 14px !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  --c: #0F172A;
  background-image:
    linear-gradient(var(--c), var(--c)),
    linear-gradient(var(--c), var(--c)),
    linear-gradient(var(--c), var(--c)),
    linear-gradient(var(--c), var(--c)),
    linear-gradient(var(--c), var(--c)),
    linear-gradient(var(--c), var(--c)),
    linear-gradient(var(--c), var(--c)),
    linear-gradient(var(--c), var(--c)) !important;
  background-position: 0 0, 0 0, 100% 0, 100% 0, 0 100%, 0 100%, 100% 100%, 100% 100% !important;
  background-size: 11px 2px, 2px 11px, 11px 2px, 2px 11px, 11px 2px, 2px 11px, 11px 2px, 2px 11px !important;
  background-repeat: no-repeat !important;
}
.f .tag,
.st-key-cov_map_ficha .tag {
  position: absolute;
  top: -22px;
  left: -1px;
  background: var(--ink);
  color: var(--white);
  font: 500 11.5px/16px var(--font-mono);
  padding: 3px 10px;
  height: 22px;
  box-sizing: border-box;
  white-space: nowrap;
  z-index: 2;
}
.st-key-cov_map_ficha {
  overflow: visible !important;
}
.st-key-cov_map_ficha > [data-testid="stVerticalBlock"],
.st-key-cov_map_ficha > [data-testid="stElementContainer"] {
  overflow: visible !important;
}
.st-key-cov_map_ficha [data-testid="stMarkdown"] {
  position: static !important;
}
.st-key-cov_map_ficha [data-testid="stElementContainer"]:has(.tag) {
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
}

/* Paneles planos para gráficas fuera de fichas con tag */
.st-key-rk_chart_card,
.st-key-cmp_cond_card,
.st-key-cmp_spread_card {
  background: var(--white) !important;
  border: 1px solid var(--line) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: 16px 18px 12px !important;
  margin-top: 8px !important;
  margin-bottom: 14px !important;
}

/* Tarjetas base usadas por app.py (planas, sin sombra ni radio > 4 px) */
.card {
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 0;
  padding: 16px 18px;
  box-shadow: none;
  margin-bottom: 14px;
}
@media (min-width: 1101px) {
  .card:not(.kpi) {
    min-height: 174px;
  }
}
.card.kpi {
  min-height: 112px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.card .l {
  color: var(--gray);
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
}
.card .v {
  font-family: var(--font-cond);
  font-size: 32px;
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: -0.01em;
  color: var(--ink);
  margin: 2px 0 4px;
}
.card .s {
  color: var(--gray);
  font-size: 12px;
  line-height: 1.4;
}

/* Franja horizontal de 3 celdas (Ranking y Cobertura) */
.strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  background: var(--white);
  border: 1px solid var(--line);
  border-radius: 0;
  box-shadow: none;
  margin-bottom: 14px;
}
.strip-cell {
  padding: 16px 20px;
  min-width: 0;
}
.strip-cell + .strip-cell {
  border-left: 1px solid var(--line);
}
.strip-l {
  font-size: 12px;
  font-weight: 500;
  color: var(--gray);
  margin-bottom: 4px;
}
.strip-v {
  font-family: var(--font-cond);
  font-size: 34px;
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: -0.01em;
  color: var(--ink);
  margin: 2px 0 4px;
}
.strip-s {
  font-size: 12px;
  color: var(--gray);
  line-height: 1.4;
}

/* Conteo numérico por CSS (@property --n) */
.cnt {
  --n: 0;
  counter-reset: num var(--n);
}
.cnt::after {
  content: counter(num);
}

/* Estado de la llama: glifo 14 px + texto en peso 600, sin fondo pastel */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  background: transparent;
  color: var(--ink);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
}
.badge svg {
  display: block;
  flex-shrink: 0;
}

/* Especificaciones con puntos guía */
.spec-list {
  margin: 10px 0 12px;
}
.spec-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  line-height: 1.7;
}
.spec-k {
  color: var(--ink);
  font-weight: 500;
}
.spec-dots {
  border-bottom: 1px dotted #B6BECA;
  transform: translateY(-3px);
  min-width: 16px;
}
.spec-v {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--ink);
  white-space: nowrap;
}

/* Cuerpo 2 columnas dentro de fichas (texto izquierda + minimapa locator derecha) */
.f-split {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.f-main {
  flex: 1 1 auto;
  min-width: 0;
}
.f-loc {
  flex: 0 0 auto;
}
.f-title {
  font-family: var(--font-cond);
  font-size: 22px;
  font-weight: 600;
  line-height: 1.15;
  color: var(--ink);
  margin: 0 0 6px 0;
}
.f-foot {
  font-size: 12px;
  color: var(--gray);
  margin-top: 10px;
  line-height: 1.45;
}

/* Enlaces DOI limpios sin pastilla gruesa */
.pill {
  display: inline-block;
  background: var(--paper);
  border: 1px solid var(--line);
  color: var(--flame) !important;
  padding: 2px 6px;
  border-radius: 3px;
  font: 500 11.5px var(--font-mono);
  text-decoration: none !important;
  margin: 2px 4px 2px 0;
}
.pill.muted {
  color: var(--gray) !important;
}

/* Barra apilada de puntaje del ensayo */
.stacked-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}
.stacked-bar {
  display: flex;
  width: 170px;
  height: 7px;
  background: var(--line);
  border-radius: 0;
  overflow: hidden;
  flex-shrink: 0;
}
.stacked-bar i {
  display: block;
  height: 100%;
  transition: width 240ms cubic-bezier(0.22, 1, 0.36, 1);
}

/* Tablas de Ranking y Comparación */
table.rk, table.cmp {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 4px;
}
table.rk th, table.rk td.n, table.rk td .pill, table.cmp th {
  white-space: nowrap;
}
table.rk th, table.cmp th {
  text-align: left;
  color: var(--gray);
  font-weight: 500;
  font-size: 12px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}
table.rk td, table.cmp td {
  padding: 10px;
  border-bottom: 1px solid var(--line);
  vertical-align: middle;
  transition: background-color 140ms ease;
}
table.rk tbody tr:hover td {
  background: rgba(246, 247, 249, 0.7);
}
table.rk tr.sel td,
table.rk tbody tr.sel:hover td {
  background: var(--paper);
}
table.rk tr.sel td:first-child {
  color: var(--flame);
  font-weight: 600;
}
table.cmp td:first-child {
  color: var(--gray);
  width: 22%;
}
table.cmp tr.d td {
  font-weight: 600;
  color: var(--ink);
  border-bottom: 1px dotted #94A3B8;
}

/* Barra de puntaje en tabla */
.score-cell, .sc {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.score-track, .stk {
  display: inline-flex;
  vertical-align: middle;
  width: 84px;
  height: 7px;
  background: var(--line);
  border-radius: 0;
  overflow: hidden;
}
.score-track i {
  display: block;
  height: 100%;
  background: var(--flame);
  transition: width 240ms cubic-bezier(0.22, 1, 0.36, 1);
}

/* Leyenda de componentes */
.comp-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 12px;
  color: var(--gray);
  margin-top: 6px;
  padding-top: 4px;
}
.comp-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.comp-dot {
  width: 9px;
  height: 9px;
  border-radius: 1px;
  display: inline-block;
}

/* Cobertura: cifra principal directamente sobre cuadrícula (sin ficha ni barra lateral) */
.gap-hero {
  padding: 4px 0 4px 0;
  margin: 4px 0 6px;
}
.gap-line {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 10px;
}
.gap-num {
  font-family: var(--font-cond);
  font-size: 56px;
  font-weight: 700;
  line-height: 1;
  color: var(--red);
}
.gap-hero.has-data .gap-num {
  color: var(--ink);
}
.gap-unit {
  font-size: 18px;
  font-weight: 500;
  color: var(--ink);
}
.gap-sub {
  font-size: 15px;
  color: var(--gray);
  margin-top: 4px;
  max-width: 72ch;
  line-height: 1.55;
}

/* Insights: cabecera, medidor de evidencia, cuerpo 44ch + locator y notas <details> */
.ins-hdr {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 12px;
}
.ins-title {
  font-family: var(--font-cond) !important;
  font-size: 22px !important;
  font-weight: 600 !important;
  line-height: 1.15 !important;
  color: var(--ink);
  margin: 0 !important;
}
.ev-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding-top: 3px;
}
.ev-lab {
  font-size: 12px;
  color: var(--gray);
  font-weight: 500;
  white-space: nowrap;
}
.ev-meter {
  display: inline-flex;
  gap: 3px;
  align-items: center;
}
.ev-meter i {
  display: inline-block;
  width: 16px;
  height: 6px;
  border-radius: 0;
  box-sizing: border-box;
}
.ins-p {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  max-width: 44ch;
  color: var(--ink);
}
.ins-p sup {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--flame);
  margin-left: 1px;
  vertical-align: super;
}
.ins-expl {
  margin-top: 8px;
  font-size: 12.5px;
  line-height: 1.5;
  max-width: 48ch;
  color: var(--gray);
}

.fn-list {
  border-top: 1px solid var(--line);
  padding-top: 10px;
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
details.cite-det {
  margin: 0;
  padding: 0;
}
summary.cite-sum {
  display: grid;
  grid-template-columns: 18px 1fr auto;
  align-items: baseline;
  gap: 6px;
  cursor: pointer;
  list-style: none;
  padding: 2px 0;
}
summary.cite-sum::-webkit-details-marker {
  display: none;
}
summary.cite-sum:focus-visible {
  outline: 2px solid var(--flame);
  outline-offset: 2px;
  border-radius: 2px;
}
.cite-num {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--gray);
}
.cite-ref {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--gray);
  min-width: 0;
  overflow-wrap: anywhere;
}
.cite-toggle {
  font-size: 12px;
  font-weight: 600;
  color: var(--flame);
  white-space: nowrap;
}
.cite-toggle::after {
  content: "Ver cita";
}
details.cite-det[open] .cite-toggle::after {
  content: "Ocultar cita";
}
.cite-q {
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--ink);
  margin: 5px 0 6px 24px;
  padding-left: 10px;
  border-left: 2px solid #CBD5E1;
  max-width: 64ch;
  overflow: hidden;
}
details::details-content {
  transition: height 180ms cubic-bezier(0.22, 1, 0.36, 1), opacity 180ms ease, content-visibility 180ms allow-discrete;
  height: 0;
  opacity: 0;
  overflow: hidden;
}
details[open]::details-content {
  height: auto;
  opacity: 1;
}
.cite-noq {
  color: var(--gray);
  font-style: italic;
}
a.doi-open {
  color: var(--flame) !important;
  font-weight: 600;
  font-size: 12px;
  text-decoration: none;
  margin-left: 6px;
}
a.doi-open:hover {
  text-decoration: underline;
}

/* Expanders de Cobertura y sidebar: sin sombra ni radio > 4 px */
[data-testid="stExpander"] {
  border: 1px solid var(--line) !important;
  border-radius: 4px !important;
  background: var(--white) !important;
  box-shadow: none !important;
}
[data-testid="stExpander"] details {
  border: none !important;
  border-radius: 4px !important;
  background: transparent !important;
  box-shadow: none !important;
}
[data-testid="stExpander"] summary p {
  font-size: 13px !important;
  font-weight: 600 !important;
  color: var(--ink) !important;
}

/* Barra de pestañas superior (.st-key-top_nav), radio de 4 px */
.st-key-top_nav {
  margin-bottom: 8px;
}
.st-key-top_nav [data-testid="stHorizontalBlock"] {
  gap: 6px !important;
  align-items: center !important;
}
.st-key-top_nav [data-testid="stColumn"] {
  display: flex !important;
  align-items: stretch !important;
}
.st-key-top_nav [data-testid="stElementContainer"],
.st-key-top_nav [data-testid="stMarkdown"],
.st-key-top_nav [data-testid="stMarkdownContainer"],
.st-key-top_nav [data-testid="stPageLink"],
.st-key-top_nav [data-testid="stPageLink"] > div {
  width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}
.tab,
[data-testid="stPageLink"] a,
.st-key-top_nav [data-testid="stPageLink-NavLink"] {
  font-family: var(--font-cond) !important;
  font-size: 15px !important;
  font-weight: 500 !important;
  min-height: 36px !important;
  height: 36px !important;
  margin: 0 !important;
  padding: 7px 12px !important;
  border-radius: 4px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-sizing: border-box !important;
  white-space: nowrap !important;
  text-decoration: none !important;
  box-shadow: none !important;
}
.tab {
  background: var(--ink);
  color: var(--white);
  border: 1px solid var(--ink);
  transition: background-color 140ms ease, color 140ms ease, border-color 140ms ease;
}
.tab[data-ff-opt="off"] {
  background: var(--white) !important;
  color: var(--ink) !important;
  border: 1px solid var(--line) !important;
}
.st-key-top_nav [data-testid="stPageLink-NavLink"] {
  background: var(--white) !important;
  color: var(--ink) !important;
  border: 1px solid var(--line) !important;
  transition: border-color 140ms ease, background-color 140ms ease, color 140ms ease;
}
.st-key-top_nav [data-testid="stPageLink-NavLink"]:hover {
  border-color: var(--ink) !important;
}
.st-key-top_nav [data-testid="stPageLink-NavLink"][data-ff-opt="on"] {
  background: var(--ink) !important;
  color: var(--white) !important;
  border-color: var(--ink) !important;
}
.st-key-top_nav [data-testid="stPageLink-NavLink"] p {
  font-family: var(--font-cond) !important;
  font-size: 15px !important;
  font-weight: 500 !important;
  color: var(--ink) !important;
  margin: 0 !important;
  transition: color 140ms ease;
}
.st-key-top_nav [data-testid="stPageLink-NavLink"][data-ff-opt="on"] p {
  color: var(--white) !important;
}

/* Branding en sidebar */
.brand {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 6px;
}
.brand-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.brand-icon svg {
  display: block;
}
.brand b {
  font-family: var(--font-cond);
  font-size: 20px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.1;
}
.brand small {
  display: block;
  color: var(--gray);
  font-size: 12px;
  line-height: 1.25;
}

.demo-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: var(--paper);
  border: 1px solid var(--line);
  color: var(--gray);
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  margin-top: 8px;
  width: 100%;
  box-sizing: border-box;
}

/* Movimiento solo en el logo y cifras de Ranking bajo prefers-reduced-motion: no-preference */
@media (prefers-reduced-motion: no-preference) {
  .ff-fl {
    transform-box: fill-box;
    transform-origin: 50% 100%;
    animation: ff-k 3.4s ease-in-out infinite;
  }
  .ff-sp {
    transform-box: fill-box;
    transform-origin: 50% 50%;
    animation: ff-b 6.8s ease-in-out infinite;
  }
  .ff-orb {
    transform-box: fill-box;
    transform-origin: 50% 50%;
  }
  .brand-icon.spin-a .ff-orb {
    animation: ff-once-a 900ms ease-in-out 1 forwards;
  }
  .brand-icon.spin-b .ff-orb {
    animation: ff-once-b 900ms ease-in-out 1 forwards;
  }
  .cnt {
    animation: ff-count 0.8s ease-out both;
  }
  .cnt.cnt-a {
    animation-name: ff-count-a;
  }
  .cnt.cnt-b {
    animation-name: ff-count-b;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after, .ff-fl, .ff-sp, .ff-orb, .cnt {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

@media (max-width: 1100px) {
  [data-testid="stHorizontalBlock"]:not(.st-key-top_nav [data-testid="stHorizontalBlock"]) {
    flex-wrap: wrap !important;
    gap: 0.75rem !important;
  }
  [data-testid="stHorizontalBlock"]:not(.st-key-top_nav [data-testid="stHorizontalBlock"]) > [data-testid="stColumn"] {
    flex: 1 1 220px !important;
    min-width: 210px !important;
  }
  .block-container {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
  }
  table.rk { min-width: 900px; }
  table.cmp { min-width: 620px; }
}

@media (max-width: 760px) {
  .strip {
    grid-template-columns: 1fr;
  }
  .strip-cell + .strip-cell {
    border-left: none;
    border-top: 1px solid var(--line);
  }
  .f-split {
    flex-direction: column;
  }
  .f-loc {
    align-self: center;
  }
  .ins-hdr {
    flex-wrap: wrap;
  }
  .f, .st-key-cov_map_ficha {
    padding: 22px 16px 16px !important;
  }
}

@media (max-width: 700px) {
  [data-testid="stHorizontalBlock"]:not(.st-key-top_nav [data-testid="stHorizontalBlock"]) > [data-testid="stColumn"] {
    flex-basis: 100% !important;
    min-width: 100% !important;
  }
  .st-key-top_nav [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    gap: 3px !important;
    scrollbar-width: none;
  }
  .st-key-top_nav [data-testid="stHorizontalBlock"]::-webkit-scrollbar {
    display: none;
  }
  .st-key-top_nav [data-testid="stColumn"] {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: max-content !important;
  }
  .tab,
  .st-key-top_nav [data-testid="stPageLink-NavLink"],
  .st-key-top_nav [data-testid="stPageLink-NavLink"] p {
    min-height: 32px !important;
    height: 32px !important;
    padding: 0 7px !important;
    font-size: 12.5px !important;
  }
}
"""


_FONTS_URL = (
    "https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700"
    "&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap"
)
_CORE_CSS = re.sub(r"@import\s+url\([^)]+\);\s*", "", CSS, count=1)


_SMOOTH_BOOT_JS = """(function(){
var d=document,h=d.head,w=window;
if(!d.getElementById("ff-fonts-link")){
  var l=d.createElement("link");
  l.id="ff-fonts-link";l.rel="stylesheet";l.href=__FONTS_URL__;
  h.appendChild(l);
}
var s=d.getElementById("ff-head-css");
if(!s){s=d.createElement("style");s.id="ff-head-css";h.appendChild(s);}
var c=__CORE_CSS__;
if(s.textContent!==c)s.textContent=c;

if(!w.__ffSmooth || w.__ffSmooth.v!==3){
  var prev=w.__ffSmooth;
  var sm={
    v:3,
    t0:prev ? prev.t0 : performance.now(),
    boostOffset:prev ? prev.boostOffset : 0,
    boostStart:-1,
    boostRaf:0,
    navRaf:0,
    ease:function(x){
      return 0.5>x ? 4*x*x*x : 1-Math.pow(-2*x+2,3)/2;
    },
    orbTime:function(now){
      var base=(now-sm.t0)/1000+sm.boostOffset;
      if(sm.boostStart>0){
        var dt=now-sm.boostStart;
        if(900>dt){
          base+=9.0*sm.ease(dt/900);
        }else{
          sm.boostOffset+=9.0;
          sm.boostStart=-1;
        }
      }
      return base%900;
    },
    syncSvg:function(root){
      var svgs=(root||d).querySelectorAll(".brand-icon svg");
      var now=performance.now();
      var ot=sm.orbTime(now);
      for(var i=0;svgs.length>i;i++){
        var svg=svgs[i];
        try{svg.setCurrentTime(ot);}catch(e){}
        if(!svg.__ffPhaseSet){
          svg.__ffPhaseSet=true;
          var fl=svg.querySelector(".ff-fl");
          var sp=svg.querySelector(".ff-sp");
          var sec=(now-sm.t0)/1000;
          if(fl)fl.style.animationDelay="-"+(sec%3.4).toFixed(2)+"s";
          if(sp)sp.style.animationDelay="-"+(sec%6.8).toFixed(2)+"s";
        }
      }
    },
    triggerBoost:function(){
      var now=performance.now();
      if(sm.boostStart>0){
        var dt=Math.min(now-sm.boostStart,900);
        sm.boostOffset+=9.0*sm.ease(dt/900);
      }
      sm.boostStart=now;
      cancelAnimationFrame(sm.boostRaf);
      function step(){
        var t=performance.now();
        sm.syncSvg(d);
        if(sm.boostStart>0 && 920>(t-sm.boostStart)){
          sm.boostRaf=requestAnimationFrame(step);
        }else{
          if(sm.boostStart>0){
            sm.boostOffset+=9.0;
            sm.boostStart=-1;
          }
          sm.syncSvg(d);
        }
      }
      sm.boostRaf=requestAnimationFrame(step);
    },
    host:function(){
      var el=d.getElementById("ff-shield-host");
      if(!el){
        el=d.createElement("div");
        el.id="ff-shield-host";
        el.className="stApp";
        d.body.appendChild(el);
      }else if(el.parentNode===d.body && d.body.lastElementChild!==el){
        d.body.appendChild(el);
      }
      return el;
    },
    cleanClone:function(origRoot,node){
      var origCanv=origRoot ? origRoot.querySelectorAll("canvas") : [];
      var cloneCanv=node.querySelectorAll("canvas");
      for(var c=0;origCanv.length>c && cloneCanv.length>c;c++){
        try{
          if(origCanv[c].width>0 && origCanv[c].height>0){
            cloneCanv[c].width=origCanv[c].width;
            cloneCanv[c].height=origCanv[c].height;
            var ctx=cloneCanv[c].getContext("2d");
            if(ctx)ctx.drawImage(origCanv[c],0,0);
          }
        }catch(_e){}
      }
      if(origRoot){
        var sel="[data-testid='stVerticalBlock'], [data-testid='stVerticalBlockBorderWrapper'], [data-testid='stHorizontalBlock'], [data-testid='stColumn'], [data-testid='stElementContainer']";
        var origBlocks=origRoot.querySelectorAll(sel);
        var cloneBlocks=node.querySelectorAll(sel);
        for(var b=0;origBlocks.length>b && cloneBlocks.length>b;b++){
          var br=origBlocks[b].getBoundingClientRect();
          if(br.width>0){
            cloneBlocks[b].style.setProperty("width",br.width+"px","important");
            cloneBlocks[b].style.setProperty("max-width",br.width+"px","important");
            cloneBlocks[b].style.setProperty("min-width",br.width+"px","important");
          }
        }
      }
      var bad=node.querySelectorAll("script, style, .ff-boot");
      for(var i=0;bad.length>i;i++){
        var ec=bad[i].closest("[data-testid='stElementContainer']");
        if(ec && !ec.querySelector("svg, .brand, .f, .strip, .card, .st-key-top_nav")){
          ec.remove();
        }else{
          bad[i].remove();
        }
      }
      var ids=node.querySelectorAll("[id]");
      for(var j=0;ids.length>j;j++)ids[j].removeAttribute("id");
      return node;
    },
    clearOpts:function(){
      var opts=d.querySelectorAll("#root [data-ff-opt]");
      for(var i=0;opts.length>i;i++)opts[i].removeAttribute("data-ff-opt");
    },
    clearShield:function(){
      cancelAnimationFrame(sm.navRaf);
      d.documentElement.classList.remove("ff-waiting");
      var bc=d.querySelector("#root .block-container");
      if(bc)bc.style.minHeight="";
      var hst=d.getElementById("ff-shield-host");
      if(hst)hst.innerHTML="";
    },
    startTransition:function(mode){
      if(w.matchMedia && w.matchMedia("(prefers-reduced-motion: reduce)").matches){
        sm.clearOpts();
        return;
      }
      var mainBc=d.querySelector("#root .block-container");
      if(!mainBc){
        sm.clearOpts();
        return;
      }
      sm.clearShield();
      var hst=sm.host();
      var bcRect=mainBc.getBoundingClientRect();
      if(80>bcRect.height){
        sm.clearOpts();
        return;
      }
      var startTabEl=mainBc.querySelector(".st-key-top_nav .tab");
      var startTab=startTabEl ? (startTabEl.innerText||"").trim() : "";
      var startSig=(mainBc.innerText||"").slice(0,600)+"|"+mainBc.querySelectorAll(".f, .strip, .card, tr").length;
      mainBc.style.minHeight=Math.round(bcRect.height)+"px";

      var sbClone=null;
      if(mode==="page"){
        var sbSec=d.querySelector("#root section[data-testid='stSidebar']");
        var sbUsr=sbSec ? sbSec.querySelector("[data-testid='stSidebarUserContent']") : null;
        if(sbSec && sbUsr){
          var sRect=sbSec.getBoundingClientRect();
          var uRect=sbUsr.getBoundingClientRect();
          if(sRect.width>40 && uRect.height>40){
            sbClone=d.createElement("section");
            sbClone.setAttribute("data-testid","stSidebar");
            sbClone.style.cssText="position:fixed !important;top:"+sRect.top+"px !important;left:"+sRect.left+"px !important;width:"+sRect.width+"px !important;height:"+sRect.height+"px !important;background:#FFFFFF !important;border-right:1px solid #DDE2E8 !important;z-index:999990 !important;pointer-events:none !important;overflow:hidden !important;";
            var usrClone=sm.cleanClone(sbUsr,sbUsr.cloneNode(true));
            usrClone.style.cssText="position:fixed !important;top:"+uRect.top+"px !important;left:"+uRect.left+"px !important;width:"+uRect.width+"px !important;";
            sbClone.appendChild(usrClone);
            hst.appendChild(sbClone);
            sm.syncSvg(sbClone);
          }
        }
      }

      var bcClone=sm.cleanClone(mainBc,mainBc.cloneNode(true));
      bcClone.style.cssText="position:fixed !important;top:"+bcRect.top+"px !important;left:"+bcRect.left+"px !important;width:"+bcRect.width+"px !important;max-width:"+bcRect.width+"px !important;margin:0 !important;box-sizing:border-box !important;pointer-events:none !important;z-index:999985 !important;";
      if(mode==="filter"){
        var navInClone=bcClone.querySelector(".st-key-top_nav");
        if(navInClone)navInClone.style.opacity="0";
      }else{
        sm.clearOpts();
      }
      hst.appendChild(bcClone);
      d.documentElement.classList.add("ff-waiting");

      var tStart=performance.now();
      var sawChange=false;
      var sawStale=false;
      var startPath=location.pathname;

      function poll(){
        var elapsed=performance.now()-tStart;
        var curBc=d.querySelector("#root .block-container");
        var vb=curBc ? curBc.querySelector("[data-testid='stVerticalBlock']") : null;
        var staleCount=d.querySelectorAll("#root [data-testid='stMainBlockContainer'] [data-stale='true']").length;
        var skelCount=d.querySelectorAll("#root [data-testid='stMainBlockContainer'] [data-testid='stSkeleton']").length;

        if(mode==="page"){
          var liveTabEl=curBc ? curBc.querySelector(".st-key-top_nav .tab") : null;
          var liveTab=liveTabEl ? (liveTabEl.innerText||"").trim() : "";
          if((liveTab!=="" && liveTab!==startTab) || (elapsed>220 && location.pathname!==startPath)){
            sawChange=true;
          }
        }else{
          if(staleCount>0 || skelCount>0)sawStale=true;
          var curSig=curBc ? ((curBc.innerText||"").slice(0,600)+"|"+curBc.querySelectorAll(".f, .strip, .card, tr").length) : "";
          if((curSig!=="" && curSig!==startSig) || (sawStale && staleCount===0) || elapsed>140){
            sawChange=true;
          }
        }

        var htmlNodes=curBc ? curBc.querySelectorAll("[data-testid='stHtml']") : [];
        var anyEmptyHtml=false;
        for(var i=0;htmlNodes.length>i;i++){
          if(htmlNodes[i].innerHTML.trim()===""){anyEmptyHtml=true;break;}
        }
        var plotNodes=curBc ? curBc.querySelectorAll("[data-testid='stPlotlyChart']") : [];
        var anyEmptyPlot=false;
        for(var j=0;plotNodes.length>j;j++){
          if(!plotNodes[j].querySelector(".main-svg")){anyEmptyPlot=true;break;}
        }
        var hasNav=curBc && !!curBc.querySelector(".st-key-top_nav");
        var minChildren=mode==="page" ? 4 : 3;
        var maxPlotWait=mode==="page" ? 310 : 240;
        var maxTotalWait=mode==="page" ? 420 : 340;
        var ready=sawChange && elapsed>45 && curBc && vb && vb.children.length>=minChildren && hasNav && staleCount===0 && skelCount===0 && !anyEmptyHtml && (!anyEmptyPlot || elapsed>maxPlotWait);

        if(ready || elapsed>maxTotalWait){
          sm.syncSvg(d);
          sm.clearOpts();
          if(sbClone){sbClone.remove();sbClone=null;}
          var navClone=bcClone.querySelector(".st-key-top_nav");
          if(navClone)navClone.style.opacity="0";
          d.documentElement.classList.remove("ff-waiting");

          var durOut=mode==="page" ? 170 : 145;
          var durIn=mode==="page" ? 195 : 170;
          var dy=mode==="page" ? 4 : 3;

          if(curBc && vb){
            var ch=vb.children;
            var afterNav=false;
            for(var k=0;ch.length>k;k++){
              if(ch[k].querySelector && ch[k].querySelector(".st-key-top_nav")){
                afterNav=true;
                continue;
              }
              if(afterNav && ch[k].animate){
                ch[k].animate([
                  {opacity:0,transform:"translate3d(0,"+dy+"px,0)"},
                  {opacity:1,transform:"translate3d(0,0,0)"}
                ],{duration:durIn,easing:"cubic-bezier(0.22, 1, 0.36, 1)"});
              }
            }
          }

          if(bcClone.animate){
            var anim=bcClone.animate([
              {opacity:1,transform:"translate3d(0,0,0)"},
              {opacity:0,transform:"translate3d(0,-"+(dy-1)+"px,0)"}
            ],{duration:durOut,easing:"cubic-bezier(0.22, 1, 0.36, 1)",fill:"forwards"});
            anim.onfinish=function(){
              bcClone.remove();
              if(curBc)curBc.style.minHeight="";
            };
          }else{
            bcClone.remove();
            if(curBc)curBc.style.minHeight="";
          }
        }else{
          sm.navRaf=requestAnimationFrame(poll);
        }
      }
      sm.navRaf=requestAnimationFrame(poll);
    }
  };

  if(!w.__ffBound){
    w.__ffBound=true;
    var mo=new MutationObserver(function(){w.__ffSmooth.syncSvg(d);});
    mo.observe(d.body,{childList:true,subtree:true});

    d.addEventListener("click",function(e){
      var cur=w.__ffSmooth;
      var t=e.target;
      if(!t || !t.closest)return;

      var sum=t.closest("summary.cite-sum");
      if(sum && e.isTrusted && !(w.matchMedia && w.matchMedia("(prefers-reduced-motion: reduce)").matches)){
        var det=sum.parentElement;
        var q=det ? det.querySelector(".cite-q") : null;
        if(det && q && q.animate){
          if(det.open){
            e.preventDefault();
            var h0=q.offsetHeight;
            var ac=q.animate([
              {height:h0+"px",opacity:1,marginTop:"5px",marginBottom:"6px"},
              {height:"0px",opacity:0,marginTop:"0px",marginBottom:"0px"}
            ],{duration:155,easing:"cubic-bezier(0.22, 1, 0.36, 1)"});
            ac.onfinish=function(){det.open=false;};
          }else{
            requestAnimationFrame(function(){
              var h1=q.offsetHeight;
              if(h1>0){
                q.animate([
                  {height:"0px",opacity:0,marginTop:"0px",marginBottom:"0px"},
                  {height:h1+"px",opacity:1,marginTop:"5px",marginBottom:"6px"}
                ],{duration:185,easing:"cubic-bezier(0.22, 1, 0.36, 1)"});
              }
            });
          }
        }
        return;
      }

      var link=t.closest("a[data-testid='stPageLink-NavLink']");
      if(link && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey){
        var topNav=link.closest(".st-key-top_nav");
        if(topNav){
          var curTab=topNav.querySelector(".tab");
          if(curTab)curTab.setAttribute("data-ff-opt","off");
          link.setAttribute("data-ff-opt","on");
        }
        cur.startTransition("page");
        return;
      }

      var sbBtn=t.closest("section[data-testid='stSidebar'] button");
      if(sbBtn){
        var txt=(sbBtn.innerText||"").trim();
        var isScen=txt.indexOf("Base Lunar")!==-1 || txt.indexOf("Traje Espacial")!==-1 || txt.indexOf("ISS")!==-1;
        if(isScen){
          cur.triggerBoost();
          var wasPrimary=sbBtn.getAttribute("data-testid")==="stBaseButton-primary";
          var allBtns=d.querySelectorAll("section[data-testid='stSidebar'] button");
          for(var b=0;allBtns.length>b;b++){
            var bt=(allBtns[b].innerText||"").trim();
            if(bt.indexOf("Base Lunar")!==-1 || bt.indexOf("Traje Espacial")!==-1 || bt.indexOf("ISS")!==-1){
              allBtns[b].setAttribute("data-ff-opt","off");
            }
          }
          if(!wasPrimary)sbBtn.setAttribute("data-ff-opt","on");
        }
        cur.startTransition("filter");
        return;
      }

      var radLbl=t.closest("[data-testid='stRadioGroup'][data-orientation='horizontal'] label[data-testid='stRadioOption']");
      if(radLbl){
        var grp=radLbl.closest("[data-testid='stRadioGroup']");
        if(grp){
          var opts=grp.querySelectorAll("label[data-testid='stRadioOption']");
          for(var r=0;opts.length>r;r++)opts[r].setAttribute("data-ff-opt","off");
          radLbl.setAttribute("data-ff-opt","on");
        }
        cur.startTransition("filter");
        return;
      }

      var selOpt=t.closest("[data-baseweb='popover'] [role='option'], [data-baseweb='menu'] li, [data-baseweb='tag'] span[role='presentation']");
      if(selOpt){
        cur.startTransition("filter");
        return;
      }
    },true);

    d.addEventListener("pointerup",function(e){
      var t=e.target;
      if(t && t.closest && t.closest("section[data-testid='stSidebar'] [data-baseweb='slider']")){
        w.__ffSmooth.startTransition("filter");
      }
    },true);
  }

  w.__ffSmooth=sm;
}
w.__ffSmooth.syncSvg(d);
})();"""


def setup(title):
    import json as _json

    icon = ASSETS / "logo.png"
    st.set_page_config(
        page_title=title,
        page_icon=str(icon) if icon.exists() else "F",
        layout="wide",
        initial_sidebar_state="auto",
    )
    is_new_page = st.session_state.get("_last_page") != title
    st.session_state["_last_page"] = title
    rerun_override = (
        ""
        if is_new_page
        else ".block-container,.block-container [data-testid='stVerticalBlock'] > :has(.st-key-top_nav) ~ *{animation:none!important}"
    )
    # <span class="ff-boot"> + \u003c evitan que DOMPurify elimine <script> raíz y persiste CSS/fuentes/transiciones en <head>
    js_css = _json.dumps(_CORE_CSS).replace("<", "\\u003c")
    js_fonts = _json.dumps(_FONTS_URL).replace("<", "\\u003c")
    boot_js = _SMOOTH_BOOT_JS.replace("__FONTS_URL__", js_fonts).replace("__CORE_CSS__", js_css).replace("\n", "")
    st.html(f'<span class="ff-boot"></span><script>{boot_js}</script>', unsafe_allow_javascript=True)
    st.markdown(f"<style>{_CORE_CSS}{rerun_override}</style>", unsafe_allow_html=True)


def tabs(active):
    """Barra de navegación superior unificada con acceso a Portada y las 4 vistas."""
    all_tabs = [("Inicio", "app.py", -1)] + [(lab, path, i) for i, (lab, path) in enumerate(TABS)]
    with st.container(key="top_nav"):
        cols = st.columns([0.8, 1.05, 1.15, 1.0, 1.35])
        for col, (lab, path, idx) in zip(cols, all_tabs):
            with col:
                if idx == active:
                    st.markdown(f'<div class="tab">{E(lab)}</div>', unsafe_allow_html=True)
                else:
                    try:
                        st.page_link(path, label=lab, width="stretch")
                    except Exception:
                        st.markdown(
                            f'<div class="tab" style="background:#FFFFFF;color:#0F172A;border:1px solid #DDE2E8">{E(lab)}</div>',
                            unsafe_allow_html=True,
                        )


def clean_str(v, default="—"):
    """Devuelve texto limpio sin imprimir 'nan' ni 'None'."""
    if v is None or pd.isna(v):
        return default
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "<na>"):
        return default
    return s


def scope_label(s):
    """Traduce etiquetas de alcance de insights al español solo para presentación."""
    raw = clean_str(s, "")
    return SCOPE_LABELS.get(raw.lower(), raw.capitalize() if raw else "")


def num(v, d=1, u=""):
    """Formatea un valor numérico con decimales y unidad; devuelve '—' si es NaN."""
    val = pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]
    if pd.isna(val):
        return "—"
    unit = "" if (u is None or pd.isna(u) or str(u).strip().lower() in ("", "nan", "none", "<na>")) else str(u)
    return f"{float(val):.{d}f}{unit}"


def fmt_gravity(v):
    """Formatea gravity_level de forma limpia (soporta numérico o etiquetas como 'microgravity')."""
    raw = clean_str(v, "")
    if raw.lower() in ("microgravity", "microgravedad", "ug", "μg", "0g"):
        return "0g"
    val = pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]
    if pd.isna(val):
        return raw if raw else "—"
    return f"{float(val):g}g"


def doi_pill(doi):
    """Genera un enlace clicable al DOI o texto neutro si falta."""
    d = clean_str(doi, default="")
    if not d or d.lower() == "sin doi":
        return '<span class="pill muted">sin DOI</span>'
    return f'<a class="pill" href="https://doi.org/{E(d)}" target="_blank" rel="noopener noreferrer">{E(d)}</a>'


def kind(o):
    """Clasifica el resultado de la llama ('dg' propagó, 'ok' extinguió, 'bl' otro) en ES/EN."""
    if o is None or pd.isna(o):
        return "bl"
    o_norm = str(o).lower().replace("ó", "o").replace("í", "i")
    negations = ("no propag", "not ", "no se", "non-", "no_", "no ignit", "self_ext", "self-ext")
    if any(k in o_norm for k in ("propag", "spread", "sustain", "ignit", "burn")) and not any(
        k in o_norm for k in negations
    ):
        return "dg"
    if any(k in o_norm for k in ("extin", "quench", "no propag", "not ", "no se", "self-ext", "self_ext", "no_ignit")):
        return "ok"
    return "bl"


def outcome_counts(series):
    """Calcula (propagó, se_extinguió, porcentaje_propagó) de forma consistente con kind()."""
    kinds = [kind(v) for v in series.dropna()]
    p = sum(1 for k in kinds if k == "dg")
    x = sum(1 for k in kinds if k == "ok")
    pp = round(100 * p / (p + x)) if (p + x) > 0 else None
    return p, x, pp


def outcome_known(series):
    """(ensayos con resultado registrado, total) para explicar en qué se basa un porcentaje."""
    s = series if isinstance(series, pd.Series) else pd.Series(series)
    return int(s.map(lambda v: clean_str(v, "") != "").sum()), int(len(s))


def outcome_label(o, default="Sin dato"):
    """Traduce valores de flame_outcome tipo snake_case (datos reales) solo para mostrar."""
    raw = clean_str(o, "")
    if not raw:
        return default
    key = raw.strip().lower()
    if key in OUTCOME_LABELS:
        return OUTCOME_LABELS[key]
    return raw.replace("_", " ").capitalize() if "_" in raw else raw


def mat_label(m, default="—"):
    """Traduce material_type (gas/solid/liquid) al español solo para mostrar."""
    raw = clean_str(m, "")
    if not raw:
        return default
    return MAT_LABELS.get(raw.strip().lower(), raw.capitalize())


def badge(t, k=None):
    """Glifo de estado de llama de 14 px + etiqueta en peso 600, sin fondo."""
    raw = clean_str(t, default="Sin dato")
    txt = outcome_label(raw)
    eff = k or kind(raw)
    if eff == "dg":
        dot = '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="4" fill="#B91C1C"/></svg>'
    elif eff == "ok":
        dot = '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="#0F766E" stroke-width="1.6" stroke-dasharray="2.4 1.6"/></svg>'
    else:
        dot = '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="#64748B" stroke-width="1.6"/></svg>'
    return f'<span class="badge">{dot}<span>{E(txt)}</span></span>'


def ficha(tag, body_html):
    """Ficha de ensayo con marcas de registro en las esquinas y pestaña mono arriba a la izquierda (una sola línea)."""
    return f'<div class="f"><span class="tag">{E(str(tag))}</span>{body_html}</div>'


def strip(cells):
    """Franja blanca continua de 3 celdas separadas por divisores de 1 px (label, value_html, sub_html)."""
    inner = "".join(
        f'<div class="strip-cell"><div class="strip-l">{l}</div><div class="strip-v">{v}</div><div class="strip-s">{s}</div></div>'
        for l, v, s in cells
    )
    return f'<div class="strip">{inner}</div>'


def dot_specs(rows):
    """Rejilla de especificaciones con puntos guía (O₂ ........ 21.0 %)."""
    items = "".join(
        f'<div class="spec-row"><span class="spec-k">{E(str(k))}</span><span class="spec-dots"></span><span class="spec-v">{v}</span></div>'
        for k, v in rows
    )
    return f'<div class="spec-list">{items}</div>'


def locator(df, hi, w=104, h=84, zone=None):
    """Minimapa SVG de ubicación en el plano O₂ (%) vs Presión (kPa)."""
    z = SCEN[zone or st.session_state.get("scen") or "Base Lunar / Rover"]
    if df is not None and "pressure_kpa" in df.columns:
        p_all = pd.to_numeric(df["pressure_kpa"], errors="coerce").dropna()
        ymax = max(140.0, float(p_all.max()) * 1.05) if not p_all.empty else 140.0
    else:
        ymax = 140.0
    X = lambda o: 14 + max(0.0, min(100.0, float(o))) * (w - 20) / 100
    Y = lambda p: h - 14 - max(0.0, min(ymax, float(p))) * (h - 22) / ymax

    grid_lines = ""
    for gx in (25, 50, 75):
        grid_lines += f'<line x1="{X(gx):.1f}" y1="8" x2="{X(gx):.1f}" y2="{h-14}" stroke="#EEF1F5" stroke-width="1"/>'
    for gy in (40, 80, 120):
        if gy < ymax:
            grid_lines += f'<line x1="14" y1="{Y(gy):.1f}" x2="{w-6}" y2="{Y(gy):.1f}" stroke="#EEF1F5" stroke-width="1"/>'

    bg_pts = ""
    if df is not None and {"o2_percent", "pressure_kpa"}.issubset(df.columns):
        bg_df = df[["o2_percent", "pressure_kpa"]].apply(pd.to_numeric, errors="coerce").dropna()
        for o, p in bg_df.itertuples(index=False):
            bg_pts += f'<circle cx="{X(o):.1f}" cy="{Y(p):.1f}" r="1.8" fill="#B6BECA"/>'

    hi_pts = ""
    hi_pairs = []
    if hi is not None and not hi.empty and {"o2_percent", "pressure_kpa"}.issubset(hi.columns):
        hi_df = hi[["o2_percent", "pressure_kpa"]].apply(pd.to_numeric, errors="coerce").dropna().head(40)
        hi_pairs = list(hi_df.itertuples(index=False))
        for o, p in hi_pairs:
            hi_pts += f'<circle cx="{X(o):.1f}" cy="{Y(p):.1f}" r="6" fill="none" stroke="#E84C22" stroke-opacity=".5"/><circle cx="{X(o):.1f}" cy="{Y(p):.1f}" r="3" fill="#E84C22"/>'

    if len(hi_pairs) == 1:
        aria = f"Ubicación en O₂ y presión: O₂ {hi_pairs[0][0]:g} %, {hi_pairs[0][1]:.1f} kPa"
    elif len(hi_pairs) > 1:
        aria = f"Ubicación en O₂ y presión: {len(hi_pairs)} ensayos citados"
    else:
        aria = "Ubicación en O₂ y presión: sin ensayos destacados"

    zx0, zx1 = X(z["o2"][0]), X(z["o2"][1])
    zy0, zy1 = Y(z["p"][1]), Y(z["p"][0])
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{E(aria)}">'
        f'<rect x="14" y="8" width="{w-20}" height="{h-22}" fill="#FFFFFF" stroke="#C9D0DA"/>'
        f'{grid_lines}'
        f'<rect x="{zx0:.1f}" y="{zy0:.1f}" width="{max(1.0, zx1-zx0):.1f}" height="{max(1.0, zy1-zy0):.1f}" fill="#E84C2210" stroke="#94A3B8" stroke-dasharray="2 2"/>'
        f'{bg_pts}{hi_pts}'
        f'<text x="14" y="{h-3}" font-size="8" fill="#64748B" font-family="JetBrains Mono,monospace">O₂ 0–100 %</text></svg>'
    )


def ev_meter(st_code):
    """Medidor de evidencia de 3 segmentos (16×6 px, separación 3 px) para Insights."""
    if st_code == "":
        segs = ['<i style="background:#0F766E"></i>'] * 3
    elif st_code == "b":
        segs = [
            '<i style="background:#0F766E"></i>',
            '<i style="background:#0F766E"></i>',
            '<i style="border:1px solid #94A3B8;background:transparent"></i>',
        ]
    else:
        segs = ['<i style="border:1px solid #94A3B8;background:transparent"></i>'] * 3
    return f'<span class="ev-meter">{"".join(segs)}</span>'


# --- Compatibilidad con ambas versiones de app/data_loader.py -------------------

def _unwrap(res):
    if isinstance(res, tuple):
        return res[0], bool(res[1]) if len(res) > 1 else False
    return res, False


def rank_df(df, weights):
    """Devuelve (df_rankeado, provisional) con cualquier versión de data_loader.rank."""
    safe_w = weights if sum(weights.values()) > 0 else dict(DEFAULT_WEIGHTS)
    return _unwrap(_dl.rank(df, safe_w))


def coverage_df(df):
    """Devuelve (malla_de_conteos, provisional) con cualquier versión de data_loader.coverage_grid."""
    return _unwrap(_dl.coverage_grid(df))


def provisional_notice(provisional, what="Ranking", module="src/ranking.py"):
    if not provisional:
        return
    fn = getattr(_dl, "provisional_banner", None)
    if callable(fn):
        fn(provisional, what, module)
    else:
        st.warning(f"{what} provisional: todavía no existe {module}. Los puntajes son de relleno.")


def load_insights_any():
    """Devuelve (raw, usando_mock), donde raw es lista o dict {'insights': [...], meta...}."""
    fmt_error = getattr(_dl, "InsightsFormatError", None)
    errors = (fmt_error,) if isinstance(fmt_error, type) else ()
    try:
        res = _dl.load_insights()
    except errors as e:
        st.error(f"insights.json tiene un formato inesperado: {e}")
        return [], False
    if isinstance(res, tuple) and len(res) == 3:
        items, meta, using_mock = res
        return {**(meta or {}), "insights": items}, using_mock
    return res


def cite_md(c):
    """Línea de cita PSI · DOI · página usando el helper disponible en data_loader."""
    fn = getattr(_dl, "citation", None) or getattr(_dl, "citation_line", None)
    if callable(fn):
        return fn(c)
    doi = clean_str(c.get("doi"), "")
    link = f"[{doi}](https://doi.org/{doi})" if doi else "sin DOI"
    return f"`{clean_str(c.get('psi_id'), '?')}` · {link}"


def card(label, value, sub="", kpi=True):
    cls = "card kpi" if kpi else "card"
    return f'<div class="{cls}"><div class="l">{label}</div><div class="v">{value}</div><div class="s">{sub}</div></div>'


def extract_insights(raw):
    """Acepta tanto una lista JSON (mock) como InsightsDocument dict (schemas.py)."""
    if isinstance(raw, dict):
        items = raw.get("insights", [])
        meta = {
            "generated_at": clean_str(raw.get("generated_at"), ""),
            "model": clean_str(raw.get("model"), ""),
            "prompt_version": clean_str(raw.get("prompt_version"), ""),
        }
        return (items if isinstance(items, list) else []), meta
    if isinstance(raw, list):
        return raw, {}
    return [], {}


def norm(i):
    """Normaliza un insight del formato mock (claims/note) o schemas.py (citations/description) en un párrafo corrido con superíndices."""
    if not isinstance(i, dict):
        return dict(
            title="Insight",
            text="—",
            explanation="",
            cites=[],
            st="w",
            lab="No hay datos suficientes",
            scope="",
            psi_ids=[],
            kb="bl",
        )
    conf = clean_str(i.get("confidence"), "").lower()
    if "claims" in i:
        raw_claims = [c for c in (i.get("claims") or []) if isinstance(c, dict)]
        cites = [
            {
                **c,
                "quote": clean_str(c.get("quote"), ""),
                "claim_text": clean_str(c.get("text"), ""),
                "has_quote": bool(clean_str(c.get("quote"), "")),
            }
            for c in raw_claims
        ]
        if raw_claims:
            text = " ".join(
                f"{E(clean_str(c.get('text'), ''))}<sup>{idx}</sup>"
                for idx, c in enumerate(raw_claims, 1)
            )
        else:
            note_txt = clean_str(
                i.get("note") or i.get("description"),
                "No hay datos suficientes en los reportes consultados.",
            )
            text = E(note_txt)
        none = len(cites) == 0
        explanation = clean_str(i.get("explanation"), "")
    else:
        raw_cites = [c for c in (i.get("citations") or []) if isinstance(c, dict)]
        cites = [
            {
                **c,
                "quote": clean_str(c.get("quote"), ""),
                "claim_text": clean_str(c.get("text"), ""),
                "has_quote": bool(clean_str(c.get("quote"), "")),
            }
            for c in raw_cites
        ]
        none = i.get("evidence_status") == "insufficient_data" or len(cites) == 0
        default_desc = (
            "No hay datos suficientes en los reportes consultados."
            if none
            else "Sin descripción disponible."
        )
        desc = clean_str(i.get("description"), default_desc)
        explanation = clean_str(i.get("explanation"), "")
        sups = "".join(f"<sup>{idx}</sup>" for idx in range(1, len(cites) + 1))
        text = f"{E(desc)}{sups}"
    st_ = "w" if none else ("" if conf in ("alta", "high") else "b")
    lab = {"w": "No hay datos suficientes", "": "Evidencia sólida", "b": "Evidencia limitada"}[st_]
    raw_pids = []
    if isinstance(i.get("psi_ids"), list):
        raw_pids.extend(clean_str(p, "") for p in i["psi_ids"])
    if clean_str(i.get("psi_id"), ""):
        raw_pids.append(clean_str(i.get("psi_id"), ""))
    raw_pids.extend(clean_str(c.get("psi_id"), "") for c in cites)
    psi_ids = list(dict.fromkeys(p for p in raw_pids if p))
    scope_val = clean_str(i.get("scope"), "")
    if not scope_val and "claims" not in i:
        scope_val = "comparison" if len(psi_ids) > 1 else "experiment"
    return dict(
        title=clean_str(i.get("title") or i.get("id"), "Hallazgo"),
        text=text,
        explanation=explanation,
        cites=cites,
        st=st_,
        lab=lab,
        scope=scope_val,
        psi_ids=psi_ids,
        kb={"": "ok", "b": "bl", "w": "bl"}[st_],
    )


norm_insight = norm


def zone_count(df, name):
    if name not in SCEN:
        return 0
    z = SCEN[name]
    o2 = pd.to_numeric(df["o2_percent"], errors="coerce")
    pr = pd.to_numeric(df["pressure_kpa"], errors="coerce")
    return int((o2.between(*z["o2"]) & pr.between(*z["p"])).sum())


def nearest(df, name, n=10):
    z = SCEN[name]
    o2 = pd.to_numeric(df["o2_percent"], errors="coerce")
    pr = pd.to_numeric(df["pressure_kpa"], errors="coerce")
    dx = (z["o2"][0] - o2).clip(lower=0).fillna(100) + (o2 - z["o2"][1]).clip(lower=0).fillna(0)
    dy = (z["p"][0] - pr).clip(lower=0).fillna(100) + (pr - z["p"][1]).clip(lower=0).fillna(0)
    return df.assign(_d=dx / 100 + dy / 100).nsmallest(n, "_d").drop(columns="_d")


def style_fig(fig, h=300):
    fig.update_layout(
        height=h,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(family="Inter, sans-serif", color="#0F172A", size=12),
        hoverlabel=dict(
            bgcolor="#0F172A",
            font_color="#FFFFFF",
            bordercolor="#E84C22",
            font_family="Inter, sans-serif",
            font_size=12,
        ),
    )
    fig.update_xaxes(gridcolor="#DDE2E8", zerolinecolor="#DDE2E8")
    fig.update_yaxes(gridcolor="#DDE2E8", zerolinecolor="#DDE2E8")
    return fig


def _bounds(df, col):
    if col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return None if s.empty or s.min() == s.max() else (float(s.min()), float(s.max()))


def sidebar(df, using_mock):
    """Sidebar común a todas las páginas. Persiste controles entre rutas y devuelve (df_filtrado, pesos)."""
    ss = st.session_state
    saved = ss.setdefault("_saved_filters", {})
    cols = {"f_o2": "o2_percent", "f_pr": "pressure_kpa", "f_fl": "flow_velocity"}
    types = ["Todos"] + sorted(str(x) for x in df["material_type"].dropna().unique())

    if "scen" not in ss:
        ss["scen"] = saved.get("scen", None)
    if "f_mat" not in ss or ss["f_mat"] not in types:
        mat_init = saved.get("f_mat", "Todos")
        ss["f_mat"] = mat_init if mat_init in types else "Todos"
    for k, v in DEFAULT_WEIGHTS.items():
        wkey = "w_" + k
        if wkey not in ss:
            ss[wkey] = float(saved.get(wkey, v))

    for key, col in cols.items():
        b = _bounds(df, col)
        if b and key not in ss:
            cur = saved.get(key, b)
            if not (isinstance(cur, (tuple, list)) and len(cur) == 2):
                cur = b
            lo, hi = min(max(float(cur[0]), b[0]), b[1]), max(min(float(cur[1]), b[1]), b[0])
            ss[key] = (min(lo, hi), max(lo, hi))

    def _sync():
        saved["scen"] = ss.get("scen")
        saved["f_mat"] = ss.get("f_mat", "Todos")
        for k in DEFAULT_WEIGHTS:
            saved["w_" + k] = ss.get("w_" + k, DEFAULT_WEIGHTS[k])
        for key in cols:
            if key in ss:
                saved[key] = ss[key]

    def _on_slider_change():
        ss["scen"] = None
        _sync()

    def pick(n):
        ss["spin"] = ss.get("spin", 0) + 1
        ss["_spin_seq"] = ss.get("_spin_seq", 0) + 1
        if ss.get("scen") == n:
            ss["scen"] = None
            for key, col in (("f_o2", "o2_percent"), ("f_pr", "pressure_kpa")):
                b = _bounds(df, col)
                if b:
                    ss[key] = b
        else:
            ss["scen"] = n
            for key, col, z in (("f_o2", "o2_percent", SCEN[n]["o2"]), ("f_pr", "pressure_kpa", SCEN[n]["p"])):
                b = _bounds(df, col)
                if b:
                    lo, hi = min(max(z[0], b[0]), b[1]), max(min(z[1], b[1]), b[0])
                    ss[key] = (min(lo, hi), max(lo, hi))
        _sync()

    def reset_filters():
        ss["scen"] = None
        ss["f_mat"] = "Todos"
        for key, col in cols.items():
            b = _bounds(df, col)
            if b:
                ss[key] = b
        _sync()

    def reset_weights():
        for k, v in DEFAULT_WEIGHTS.items():
            ss["w_" + k] = v
        _sync()

    spin_click = ss.pop("spin", 0)
    spin_seq = ss.get("_spin_seq", 0)
    spin_cls = (" spin-a" if spin_seq % 2 == 1 else " spin-b") if spin_click else ""

    with st.sidebar:
        st.markdown(
            f'<div class="brand"><div class="brand-icon{spin_cls}">{LOGO}</div><div><b>Flame in Freefall</b>'
            '<small>NASA PSI · Seguridad contra incendios</small></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sec-hdr">Escenarios</div>', unsafe_allow_html=True)
        st.caption("Rangos objetivo · supuestos del equipo")
        for n in SCEN:
            st.button(
                n,
                key="b_" + n,
                on_click=pick,
                args=(n,),
                width="stretch",
                help=f"Supuesto del equipo: {SCEN[n]['desc']} (clic de nuevo para desactivar)",
                type="primary" if ss["scen"] == n else "secondary",
            )

        st.markdown('<div class="sec-hdr">Filtros físicos</div>', unsafe_allow_html=True)
        st.radio(
            "Material",
            types,
            key="f_mat",
            horizontal=True,
            format_func=lambda t: mat_label(t) if t != "Todos" else t,
            on_change=_sync,
        )
        rng = {}
        for key, label in (("f_o2", "Oxígeno (%)"), ("f_pr", "Presión (kPa)"), ("f_fl", "Flujo (cm/s)")):
            b = _bounds(df, cols[key])
            rng[key] = None
            if b:
                cb = _on_slider_change if key in ("f_o2", "f_pr") else _sync
                rng[key] = st.slider(label, b[0], b[1], key=key, on_change=cb)

        has_active_filter = bool(ss.get("scen")) or ss.get("f_mat", "Todos") != "Todos" or any(
            rng[k] is not None and rng[k] != _bounds(df, cols[k]) for k in cols
        )
        if has_active_filter:
            st.button("Limpiar filtros", key="b_reset_filters", on_click=reset_filters, width="stretch")

        with st.expander("Ajustar pesos del ranking"):
            for k in DEFAULT_WEIGHTS:
                st.slider(COMP_LABELS.get(k, k.capitalize()), 0.0, 1.0, step=0.05, key="w_" + k, on_change=_sync)
            st.button("Restablecer pesos", on_click=reset_weights, width="stretch")

        if using_mock:
            st.markdown(
                '<div class="demo-pill"><svg width="8" height="8" viewBox="0 0 8 8" aria-hidden="true"><circle cx="4" cy="4" r="3" fill="#64748B"/></svg>'
                '<span>Modo demo · datos de ejemplo</span></div>',
                unsafe_allow_html=True,
            )

    _sync()
    f = df if ss["f_mat"] == "Todos" else df[df["material_type"].astype(str) == ss["f_mat"]]
    active_scen = ss.get("scen")
    if active_scen in SCEN:
        z = SCEN[active_scen]
        o2_s = pd.to_numeric(f["o2_percent"], errors="coerce")
        pr_s = pd.to_numeric(f["pressure_kpa"], errors="coerce")
        f = f[o2_s.between(*z["o2"]) & pr_s.between(*z["p"])]
        if rng.get("f_fl"):
            fl_s = pd.to_numeric(f["flow_velocity"], errors="coerce")
            f = f[fl_s.isna() | fl_s.between(*rng["f_fl"])]
    else:
        for key, r in rng.items():
            if r:
                col_s = pd.to_numeric(f[cols[key]], errors="coerce")
                f = f[col_s.isna() | col_s.between(*r)]
    return f, {k: ss["w_" + k] for k in DEFAULT_WEIGHTS}
