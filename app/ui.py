"""Capa visual (solo frontend): CSS, animaciones, componentes HTML y sidebar compartido.
No toca datos ni ranking: todo sale de data_loader."""
from html import escape as E

import pandas as pd
import streamlit as st

from data_loader import DEFAULT_WEIGHTS

SCEN = {  # zonas objetivo: o2 (%), presion (kPa) — supuestos del equipo pendientes de validar
    "Base Lunar / Rover": {"o2": (30, 60), "p": (0, 70.3), "desc": "O₂ 30–60% · ≤70.3 kPa"},
    "Traje Espacial": {"o2": (90, 100), "p": (0, 35), "desc": "O₂ 90–100% · ≤35 kPa"},
    "ISS / Tierra": {"o2": (19, 23), "p": (95, 102), "desc": "O₂ 19–23% · 95–102 kPa"},
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

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg-canvas: #F6F7F9;
  --bg-surface: #FFFFFF;
  --border-subtle: #E5E7EB;
  --border-hover: #CBD5E1;
  --text-primary: #0F172A;
  --text-secondary: #64748B;
  --accent-nasa: #E84C22;
  --accent-nasa-soft: #FFF1ED;
  --status-danger: #B91C1C;
  --status-danger-bg: #FEF2F2;
  --status-warning: #B45309;
  --status-warning-bg: #FFFBEB;
  --status-success: #15803D;
  --status-success-bg: #F0FDF4;
  --status-info: #1D4ED8;
  --status-info-bg: #EFF6FF;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInFast {
  from { opacity: 0; transform: translateY(3px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes growBar {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}

@keyframes drawBorderY {
  from { transform: scaleY(0); }
  to { transform: scaleY(1); }
}

@keyframes scenPulse {
  0% { box-shadow: 0 0 0 0 rgba(232, 76, 34, 0.42), 0 3px 10px rgba(232, 76, 34, 0.25); }
  100% { box-shadow: 0 0 0 6px rgba(232, 76, 34, 0), 0 3px 10px rgba(232, 76, 34, 0.25); }
}

@keyframes bannerPulse {
  0% { transform: translateY(4px); opacity: 0; }
  60% { transform: translateY(0); opacity: 1; }
  100% { transform: translateY(0); opacity: 1; }
}

@keyframes pulseDot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(0.88); }
}

@keyframes bootFadeOut {
  0% { opacity: 0; transform: translateY(-6px); }
  15% { opacity: 1; transform: translateY(0); }
  78% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(-6px); visibility: hidden; }
}

html, body, .stApp, [class*="css"] {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color: var(--text-primary);
}

[data-testid="stSidebarNav"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* Indicador nativo de carga de Streamlit estilizado como telemetría */
[data-testid="stStatusWidget"] {
  background: #0F172A !important;
  color: #F8FAFC !important;
  border-radius: 999px !important;
  padding: 4px 12px !important;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15) !important;
  transition: opacity 0.2s var(--ease-out), transform 0.2s var(--ease-out) !important;
}
[data-testid="stStatusWidget"] * {
  color: #F8FAFC !important;
  font-size: 12px !important;
}

.block-container {
  padding: 1rem clamp(1rem, 2.4vw, 2.2rem) 2.5rem !important;
  max-width: 1460px !important;
}

/* Sidebar: eliminar hueco superior excesivo conservando botón de colapso */
section[data-testid="stSidebar"] {
  background: #FFFFFF !important;
  border-right: 1px solid var(--border-subtle) !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
  height: auto !important;
  min-height: 28px !important;
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
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
  margin: 12px 0 4px 0;
}

/* Botones de escenario en sidebar (selectores descendientes compatibles con tooltip wrapper de Streamlit 1.67) */
section[data-testid="stSidebar"] [data-testid^="stBaseButton-"] {
  border-radius: 7px !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  min-height: 36px !important;
  padding: 0.42rem 0.75rem !important;
  transition: background-color 0.18s var(--ease-out), color 0.18s var(--ease-out), border-color 0.18s var(--ease-out), transform 0.18s var(--ease-out), box-shadow 0.18s var(--ease-out) !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
  background-color: #EEF1F5 !important;
  color: #1E293B !important;
  border: 1px solid #E2E8F0 !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
  background-color: #E2E8F0 !important;
  border-color: #CBD5E1 !important;
  transform: translateY(-1px);
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
  background-color: var(--accent-nasa) !important;
  color: #FFFFFF !important;
  border: 1px solid #D03E16 !important;
  box-shadow: 0 3px 10px rgba(232, 76, 34, 0.25) !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p {
  color: #FFFFFF !important;
  font-weight: 600 !important;
}
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {
  background-color: #D9431A !important;
  transform: translateY(-1px);
}

/* Radio horizontal tipo Segmented Control (DOM exacto de Streamlit 1.67: stRadioGroup > div > label[data-testid="stRadioOption"]) */
[data-testid="stRadioGroup"][data-orientation="horizontal"] {
  background: #EEF1F5 !important;
  padding: 4px !important;
  border-radius: 8px !important;
  gap: 4px !important;
  display: inline-flex !important;
  flex-wrap: wrap !important;
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
  padding: 5px 11px !important;
  border-radius: 6px !important;
  background: transparent !important;
  transition: background-color 0.18s var(--ease-out), box-shadow 0.18s var(--ease-out), transform 0.18s var(--ease-out) !important;
  cursor: pointer !important;
}
/* Ocultar el círculo de radio nativo dentro de stRadioOption */
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {
  display: none !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p {
  font-size: 12.5px !important;
  font-weight: 500 !important;
  color: #475569 !important;
  margin: 0 !important;
  text-align: center !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"][data-selected="true"],
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"]:has(input:checked) {
  background: #FFFFFF !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12) !important;
}
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"][data-selected="true"] [data-testid="stMarkdownContainer"] p,
[data-testid="stRadioGroup"][data-orientation="horizontal"] label[data-testid="stRadioOption"]:has(input:checked) [data-testid="stMarkdownContainer"] p {
  color: #0F172A !important;
  font-weight: 600 !important;
}

.mono, .n {
  font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace;
  font-variant-numeric: tabular-nums;
}

/* Tarjetas KPI y contenedores */
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  margin-bottom: 14px;
  transition: transform 0.2s var(--ease-out), box-shadow 0.2s var(--ease-out), border-color 0.2s var(--ease-out);
}
.card:hover {
  border-color: var(--border-hover);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}
.card.kpi {
  min-height: 110px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.card.kpi:hover {
  transform: translateY(-2px);
}
.card .l {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
}
.card .v {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  margin: 2px 0 4px;
  line-height: 1.2;
}
.card .s {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.4;
}

/* Insignias semánticas */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 4px;
  font-size: 11.5px;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
}
.badge::before {
  content: "";
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.dg { background: var(--status-danger-bg); color: var(--status-danger); }
.ok { background: var(--status-success-bg); color: var(--status-success); }
.bl { background: var(--status-info-bg); color: var(--status-info); }
.wn { background: var(--status-warning-bg); color: var(--status-warning); }

/* Pills y enlaces DOI */
.pill {
  display: inline-block;
  background: #EEF1F5;
  color: #334155;
  padding: 3px 8px;
  border-radius: 4px;
  font: 500 11.5px 'JetBrains Mono', monospace;
  text-decoration: none !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  transition: background-color 0.15s ease, color 0.15s ease, transform 0.15s ease;
  margin: 2px 4px 2px 0;
}
a.pill:hover {
  background: #E2E8F0;
  color: #0F172A;
  transform: translateY(-1px);
}
.pill.muted {
  color: #94A3B8;
  background: #F1F5F9;
}

/* Barra proporcional de resultado dominante */
.prop {
  display: flex;
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  margin-top: 9px;
  background: #E5E7EB;
  transform-origin: left center;
}
.prop i {
  display: block;
  height: 100%;
}

/* Tablas de Ranking y Comparación */
table.rk, table.cmp {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 8px;
}
table.rk th, table.cmp th {
  text-align: left;
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  padding: 10px 10px;
  border-bottom: 1px solid var(--border-subtle);
  background: #FAFBFD;
}
table.rk td, table.cmp td {
  padding: 11px 10px;
  border-bottom: 1px solid #F1F5F9;
  vertical-align: middle;
}
table.rk tbody tr {
  transition: background-color 0.15s ease;
}
table.rk tbody tr:hover {
  background-color: #F8FAFC;
}
table.rk tbody tr.top-row {
  background-color: #FFF8F6;
}
table.rk tbody tr.top-row td:first-child {
  border-left: 3px solid var(--accent-nasa);
  font-weight: 600;
  color: var(--accent-nasa);
}
table.rk tbody tr.top-row:hover {
  background-color: #FFF1ED;
}
table.cmp td:first-child {
  color: var(--text-secondary);
  font-weight: 500;
  width: 20%;
}
table.cmp tr.d td {
  background: #FFFBEB;
}
table.cmp tr.d td:first-child {
  border-left: 3px solid #D97706;
  color: #92400E;
  font-weight: 600;
}

/* Barra de puntaje en tabla (crece con transform: scaleX sin reflow) */
.score-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.score-track {
  display: inline-flex;
  vertical-align: middle;
  width: 82px;
  height: 8px;
  background: #E5E7EB;
  border-radius: 4px;
  overflow: hidden;
}
.score-track i {
  display: block;
  width: 100%;
  height: 100%;
  background: var(--accent-nasa);
  transform-origin: left center;
}

/* Leyenda de componentes */
.comp-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 8px;
  padding-top: 6px;
}
.comp-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.comp-dot {
  width: 9px;
  height: 9px;
  border-radius: 2px;
  display: inline-block;
}

/* Tarjetas de Insights con borde izquierdo animado ::before y unión al expander */
.find {
  position: relative;
  overflow: hidden;
  padding-left: 20px;
}
.find::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--status-success);
  transform-origin: top center;
}
.find.b::before {
  background: var(--status-info);
}
.find.w::before {
  background: #D97706;
}
.find:hover {
  transform: translateY(-2px);
}
.find.has-cites {
  margin-bottom: 0 !important;
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  border-bottom: none !important;
}
.find .h {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.find h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}
.find p {
  margin: 8px 0 12px;
  line-height: 1.55;
  color: #334155;
  font-size: 13.5px;
}
.find .meta-line {
  font-size: 11.5px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

/* Expander unido a la tarjeta de Insight y animación de chevron */
[data-testid="stExpander"] details {
  border-color: var(--border-subtle) !important;
  border-radius: 8px !important;
  background: #FFFFFF !important;
}
[data-testid="stExpander"] summary [data-testid="stIconMaterial"] {
  transition: transform 0.2s var(--ease-out) !important;
}
.insight-block [data-testid="stExpander"] {
  margin-top: -14px !important;
  margin-bottom: 14px !important;
}
.insight-block [data-testid="stExpander"] details {
  border-top-left-radius: 0 !important;
  border-top-right-radius: 0 !important;
  border-bottom-left-radius: 10px !important;
  border-bottom-right-radius: 10px !important;
  background: #FAFBFD !important;
  border-top: 1px dashed #E2E8F0 !important;
}

/* Banner de alerta de vacío */
.ban {
  background: var(--status-warning-bg);
  border: 1px solid #F5D9A6;
  border-left: 4px solid #D97706;
  border-radius: 8px;
  padding: 12px 16px;
  color: var(--status-warning);
  font-weight: 500;
  font-size: 13.5px;
  margin-bottom: 16px;
}

/* Barra de pestañas superior unificada (.st-key-top_nav) */
.st-key-top_nav {
  margin-bottom: 6px;
}
.st-key-top_nav [data-testid="stHorizontalBlock"] {
  background: #E8EBF0;
  padding: 4px;
  border-radius: 10px;
  gap: 4px !important;
  align-items: center !important;
}
.st-key-top_nav [data-testid="stColumn"] {
  display: flex !important;
  align-items: stretch !important;
}
.st-key-top_nav [data-testid="stElementContainer"],
.st-key-top_nav [data-testid="stMarkdown"],
.st-key-top_nav [data-testid="stPageLink"],
.st-key-top_nav [data-testid="stPageLink"] > div {
  width: 100% !important;
  margin: 0 !important;
}
.tab,
.st-key-top_nav [data-testid="stPageLink-NavLink"] {
  min-height: 36px !important;
  height: 36px !important;
  margin: 0 !important;
  padding: 0 12px !important;
  border-radius: 7px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-sizing: border-box !important;
  white-space: nowrap !important;
}
.tab {
  background: #0F172A;
  color: #FFFFFF;
  font-size: 13.5px;
  font-weight: 600;
  box-shadow: inset 0 -2.5px 0 var(--accent-nasa), 0 2px 6px rgba(15, 23, 42, 0.16);
  user-select: none;
}
.st-key-top_nav [data-testid="stPageLink-NavLink"] {
  background: transparent !important;
  border: none !important;
  transition: background-color 0.18s var(--ease-out), color 0.18s var(--ease-out) !important;
}
.st-key-top_nav [data-testid="stPageLink-NavLink"]:hover {
  background: rgba(255, 255, 255, 0.65) !important;
}
.st-key-top_nav [data-testid="stPageLink-NavLink"] p {
  font-size: 13.5px !important;
  font-weight: 500 !important;
  color: #334155 !important;
  margin: 0 !important;
}

/* Branding en sidebar */
.brand {
  display: flex;
  gap: 11px;
  align-items: center;
  margin-bottom: 6px;
  padding-bottom: 8px;
  border-bottom: 1px solid #F1F5F9;
}
.brand-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #FFF1ED;
  border: 1px solid #FFD6C9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.brand b {
  font-size: 15.5px;
  font-weight: 700;
  color: #0F172A;
  letter-spacing: -0.01em;
}
.brand small {
  display: block;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.2;
}

/* Estado pie de sidebar */
.demo-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: #F1F5F9;
  border: 1px solid #E2E8F0;
  color: #475569;
  padding: 5px 10px;
  border-radius: 6px;
  font: 500 11.5px 'Inter', sans-serif;
  margin-top: 8px;
  width: 100%;
  box-sizing: border-box;
}
.demo-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #D97706;
  flex-shrink: 0;
}

/* Toast no bloqueante de telemetría inicial (arriba a la derecha, sin tapar tablas ni matrices) */
.boot-toast {
  position: fixed;
  top: 12px;
  right: 16px;
  z-index: 9999;
  pointer-events: none;
  background: #0F172A;
  color: #F8FAFC;
  border-left: 3px solid var(--accent-nasa);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 500;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.18);
  display: flex;
  align-items: center;
  gap: 7px;
  animation: bootFadeOut 1.6s var(--ease-out) forwards;
}

/* Animaciones condicionadas a prefers-reduced-motion: no-preference */
@media (prefers-reduced-motion: no-preference) {
  .demo-dot {
    animation: pulseDot 2.2s infinite ease-in-out;
  }
  section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    animation: scenPulse 0.42s var(--ease-out) 1;
  }
  [data-testid="stExpander"] details[open] [data-testid="stExpanderDetails"] {
    animation: fadeInFast 0.2s var(--ease-out) both;
  }
  .block-container {
    animation: fadeInUp 0.22s var(--ease-out) both;
  }
  .card {
    animation: fadeInUp 0.24s var(--ease-out) both;
  }
  /* Entrada escalonada de tarjetas KPI */
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) .card.kpi { animation-delay: 0ms; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) .card.kpi { animation-delay: 55ms; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) .card.kpi { animation-delay: 110ms; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4) .card.kpi { animation-delay: 165ms; }
  /* Aparición escalonada corta en filas de tabla de ranking */
  table.rk tbody tr {
    animation: fadeInFast 0.18s var(--ease-out) both;
  }
  table.rk tbody tr:nth-child(1) { animation-delay: 15ms; }
  table.rk tbody tr:nth-child(2) { animation-delay: 30ms; }
  table.rk tbody tr:nth-child(3) { animation-delay: 45ms; }
  table.rk tbody tr:nth-child(4) { animation-delay: 60ms; }
  table.rk tbody tr:nth-child(5) { animation-delay: 75ms; }
  table.rk tbody tr:nth-child(6) { animation-delay: 90ms; }
  table.rk tbody tr:nth-child(7) { animation-delay: 105ms; }
  table.rk tbody tr:nth-child(8) { animation-delay: 120ms; }
  table.rk tbody tr:nth-child(9) { animation-delay: 135ms; }
  table.rk tbody tr:nth-child(10) { animation-delay: 150ms; }
  .prop,
  .score-track i {
    animation: growBar 0.35s var(--ease-out) both;
  }
  .find::before {
    animation: drawBorderY 0.28s var(--ease-out) both;
  }
  .ban {
    animation: bannerPulse 0.32s var(--ease-out) 1 both;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
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
  .card { padding: 14px; }
  table.rk { min-width: 900px; }
  table.cmp { min-width: 620px; }
}

@media (max-width: 700px) {
  [data-testid="stHorizontalBlock"]:not(.st-key-top_nav [data-testid="stHorizontalBlock"]) > [data-testid="stColumn"] {
    flex-basis: 100% !important;
    min-width: 100% !important;
  }
  /* En móvil, mantener las pestañas en una sola fila horizontal con scroll sin apilarlas */
  .st-key-top_nav [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    gap: 4px !important;
    padding: 4px !important;
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
  .st-key-top_nav [data-testid="stPageLink-NavLink"] {
    min-height: 32px !important;
    height: 32px !important;
    padding: 0 7px !important;
    font-size: 11.5px !important;
  }
  .st-key-top_nav [data-testid="stPageLink-NavLink"] p {
    font-size: 11.5px !important;
  }
  .find .h { flex-wrap: wrap; }
}
"""


def setup(title):
    st.set_page_config(page_title=title, page_icon="🔥", layout="wide", initial_sidebar_state="auto")
    is_new_page = st.session_state.get("_last_page") != title
    st.session_state["_last_page"] = title
    rerun_override = (
        ""
        if is_new_page
        else ".block-container,.card,table.rk tbody tr,.prop,.score-track i,.find::before,.ban{animation:none!important}"
    )
    st.markdown(f"<style>{CSS}{rerun_override}</style>", unsafe_allow_html=True)
    if not st.session_state.get("_boot_shown"):
        st.session_state["_boot_shown"] = True
        st.markdown(
            '<div class="boot-toast"><span class="demo-dot" style="background:#22C55E"></span>'
            '<span>NASA PSI · Evidencia precalculada lista</span></div>',
            unsafe_allow_html=True,
        )


def tabs(active):
    """Barra de navegación superior unificada con acceso a Portada y las 4 vistas."""
    all_tabs = [("Inicio", "app.py", -1)] + [(lab, path, i) for i, (lab, path) in enumerate(TABS)]
    with st.container(key="top_nav"):
        cols = st.columns([0.8, 1.1, 1.1, 1.1, 1.3])
        for col, (lab, path, idx) in zip(cols, all_tabs):
            with col:
                if idx == active:
                    st.markdown(f'<div class="tab">{E(lab)}</div>', unsafe_allow_html=True)
                else:
                    try:
                        st.page_link(path, label=lab, width="stretch")
                    except Exception:
                        st.markdown(
                            f'<div class="tab" style="background:transparent;color:#334155;box-shadow:none">{E(lab)}</div>',
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
    """Formatea gravity_level de forma limpia."""
    val = pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]
    if pd.isna(val):
        return "—"
    return f"{float(val):g}g"


def doi_pill(doi):
    """Genera un enlace clicable al DOI o una píldora neutra si falta."""
    d = clean_str(doi, default="")
    if not d or d.lower() == "sin doi":
        return '<span class="pill muted">sin DOI</span>'
    return f'<a class="pill" href="https://doi.org/{E(d)}" target="_blank" rel="noopener noreferrer">{E(d)}</a>'


def kind(o):
    """Color de la insignia según el texto de flame_outcome (ES/EN, con o sin tildes)."""
    if o is None or pd.isna(o):
        return "bl"
    o_norm = str(o).lower().replace("ó", "o").replace("í", "i")
    if any(k in o_norm for k in ("propag", "spread", "sustain", "ignit", "burn")) and not any(
        k in o_norm for k in ("no propag", "not ", "no se", "non-")
    ):
        return "dg"
    if any(k in o_norm for k in ("extin", "quench", "no propag", "not ", "no se", "self-ext")):
        return "ok"
    return "bl"


def outcome_counts(series):
    """Calcula (propagó, se_extinguió, porcentaje_propagó) de forma consistente con kind()."""
    kinds = [kind(v) for v in series.dropna()]
    p = sum(1 for k in kinds if k == "dg")
    x = sum(1 for k in kinds if k == "ok")
    pp = round(100 * p / (p + x)) if (p + x) > 0 else None
    return p, x, pp


def badge(t, k=None):
    txt = clean_str(t, default="Sin dato")
    return f'<span class="badge {k or kind(txt)}">{E(txt)}</span>'


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


def norm_insight(i):
    """Normaliza un insight individual del formato mock (claims/note) o schemas.py (citations/description)."""
    if not isinstance(i, dict):
        return dict(title="Insight", text="—", explanation="", cites=[], st="w", lab="No hay datos suficientes", scope="", psi_ids=[], kb="wn")
    conf = clean_str(i.get("confidence"), "").lower()
    if "claims" in i:
        raw_claims = i.get("claims") or []
        cites = [{**c, "quote": c.get("quote") or c.get("text") or ""} for c in raw_claims if isinstance(c, dict)]
        if raw_claims:
            text = "<br>".join("• " + E(clean_str(c.get("text"), "")) for c in raw_claims if isinstance(c, dict))
        else:
            note_txt = clean_str(i.get("note") or i.get("description"), "No hay datos suficientes en los reportes consultados.")
            text = E(note_txt)
        none = len(cites) == 0
        explanation = clean_str(i.get("explanation"), "")
    else:
        raw_cites = i.get("citations") or []
        cites = [c for c in raw_cites if isinstance(c, dict)]
        desc = clean_str(i.get("description"), "Sin descripción disponible.")
        explanation = clean_str(i.get("explanation"), "")
        text = E(desc)
        none = i.get("evidence_status") == "insufficient_data" or len(cites) == 0
    st_ = "w" if none else ("" if conf in ("alta", "high") else "b")
    lab = {"w": "No hay datos suficientes", "": "Evidencia sólida", "b": "Evidencia limitada"}[st_]
    psi_ids = i.get("psi_ids") or list(dict.fromkeys(clean_str(c.get("psi_id"), "") for c in cites if clean_str(c.get("psi_id"), "")))
    return dict(
        title=clean_str(i.get("title") or i.get("id"), "Hallazgo"),
        text=text,
        explanation=explanation,
        cites=cites,
        st=st_,
        lab=lab,
        scope=clean_str(i.get("scope"), ""),
        psi_ids=psi_ids,
        kb={"": "ok", "b": "bl", "w": "wn"}[st_],
    )


def zone_count(df, name):
    if name not in SCEN:
        return 0
    z = SCEN[name]
    return int((df["o2_percent"].between(*z["o2"]) & df["pressure_kpa"].between(*z["p"])).sum())


def nearest(df, name, n=10):
    z = SCEN[name]
    dx = (z["o2"][0] - df["o2_percent"]).clip(lower=0).fillna(100) + (df["o2_percent"] - z["o2"][1]).clip(lower=0).fillna(0)
    dy = (z["p"][0] - df["pressure_kpa"]).clip(lower=0).fillna(100) + (df["pressure_kpa"] - z["p"][1]).clip(lower=0).fillna(0)
    return df.assign(_d=dx / 100 + dy / 100).nsmallest(n, "_d").drop(columns="_d")


def style_fig(fig, h=300):
    fig.update_layout(
        height=h,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=42, b=10),
        font=dict(family="Inter, sans-serif", color="#0F172A", size=12),
        title=dict(font=dict(size=13.5, color="#0F172A"), x=0, xanchor="left"),
        transition=dict(duration=300, easing="cubic-in-out"),
        hoverlabel=dict(
            bgcolor="#0F172A",
            font_color="#F8FAFC",
            bordercolor="#E84C22",
            font_family="Inter, sans-serif",
            font_size=12,
        ),
    )
    fig.update_xaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    fig.update_yaxes(gridcolor="#E5E7EB", zerolinecolor="#E5E7EB")
    return fig


def _bounds(df, col):
    if col not in df.columns:
        return None
    s = df[col].dropna()
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

    with st.sidebar:
        st.markdown(
            '<div class="brand"><div class="brand-icon">🔥</div><div><b>Flame in Freefall</b>'
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
            format_func=lambda t: t.capitalize() if t != "Todos" else t,
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
                '<div class="demo-pill"><span class="demo-dot"></span>'
                '<span>Modo Demo · datos de ejemplo</span></div>',
                unsafe_allow_html=True,
            )

    _sync()
    f = df if ss["f_mat"] == "Todos" else df[df["material_type"].astype(str) == ss["f_mat"]]
    active_scen = ss.get("scen")
    if active_scen in SCEN:
        z = SCEN[active_scen]
        f = f[f["o2_percent"].between(*z["o2"]) & f["pressure_kpa"].between(*z["p"])]
        if rng.get("f_fl"):
            f = f[f["flow_velocity"].isna() | f["flow_velocity"].between(*rng["f_fl"])]
    else:
        for key, r in rng.items():
            if r:
                f = f[f[cols[key]].isna() | f[cols[key]].between(*r)]
    return f, {k: ss["w_" + k] for k in DEFAULT_WEIGHTS}
