# Por qué un experimento va primero (Python 2)

Cada afirmación lleva una etiqueta: **[Fuente]** (hay documento NASA que la respalda) o
**[Supuesto del equipo]** (decisión nuestra; los jueces pueden preguntarla y se puede cambiar).

`rank(df, weights)` devuelve las mismas filas con `score_relevancia`, `score_riesgo`,
`score_evidencia`, `score_cobertura` y `score_total`, todos entre 0 y 1.

    score_total = Σ peso_i × score_i      (los pesos se normalizan para sumar 1)

`rank_contributions(ranked, weights)` da cuánto aporta cada componente (suman `score_total`):
es el desglose para explicar el orden. **Un dato faltante nunca suma puntaje**: queda en 0 y no se
inventa. Los pesos son ajustables en la interfaz. **[Supuesto del equipo]**: los pesos iniciales
(0.35 / 0.20 / 0.25 / 0.20).

## score_relevancia — «¿qué tan parecidas son las condiciones a una cabina real?»
Distancia de (O2 %, presión kPa) a las atmósferas de referencia (los centros, de NASA):

| Referencia | O2 % | Presión | Fuente |
|---|---|---|---|
| Hábitat de exploración (Luna/Marte) | 34 | 8.2 psia = 56.5 kPa | [Fuente] NTRS 20240005117, 20220005709 |
| Nave/ISS a nivel del mar | 21 | 14.7 psia = 101.35 kPa | [Fuente] NTRS 20240005117 |

d = √[ ((O2 − O2ref)/20)² + ((P − Pref)/50)² ];  relevancia = máx sobre referencias de max(0, 1 − d).
1 = idéntica a una referencia; 0 = a 20 puntos de O2 o 50 kPa (o más). Si falta O2 o presión → 0.

- **Por qué esta lógica [Fuente]:** a menor presión se necesita más oxígeno, y eso puede aumentar el
  riesgo de incendio (NTRS 20220015741). Por eso el hábitat de exploración combina presión baja con
  34 % de O2, y los ensayos cerca de esa combinación son los más informativos para Luna y Marte.
- **Las escalas 20 puntos de O2 y 50 kPa [Supuesto del equipo].**
- Con los botones de escenario se usa `rank_scenario` (ver abajo): la misma fórmula, pero medida
  contra el rango del escenario en vez de contra un punto.

## score_riesgo — «¿se observó propagación de la llama?»
Según `flame_outcome`: propagó = 1, otro = 0.5, se extinguió = 0, «no propagó» = 0, sin dato = 0.

- **Por qué [Fuente, secundaria]:** que la llama se propague más allá de un límite es el criterio de
  falla de la prueba de materiales NASA-STD-6001B (nota de Fire & Safety Journal, 2026:
  https://fireandsafetyjournalamericas.com/nasa-to-test-fire-on-the-moon/). Un ensayo donde propagó
  informa más sobre el peligro, por eso sube en el ranking.
- **Los valores 1 / 0.5 / 0 [Supuesto del equipo].** «Riesgo alto» significa «informa más sobre el
  peligro», no «es más seguro». Si el equipo prefiere lo contrario, se invierte con
  `higher_is_better=False` en `rank_master`.
- Este componente NO usa la tasa de propagación (`flame_spread_rate`): sus unidades pueden diferir
  entre investigaciones. `check_master` avisa si hay unidades mezcladas.

## score_evidencia — «¿qué tan sólida y documentada es la evidencia?»  [Supuesto del equipo]
0.5 × min(ensayos de su investigación / 10, 1) + 0.5 × completitud de la fila
(O2, presión, flujo, resultado, tasa, página y DOI presentes). La consistencia entre ensayos queda
fuera de la v0.

## score_cobertura — «¿cuántas condiciones distintas explora su investigación?»  [Supuesto del equipo]
Combinaciones distintas de (O2, presión, flujo) de su `psi_id`, divididas entre las de la
investigación que más explora en la tabla (1 = la que más).

## Escenarios (`src/scenarios.py`, definidos UNA vez en `SCENARIOS`)
Rangos inclusivos. Los centros salen de documentos NASA; **los márgenes son [Supuesto del equipo]**.

| Botón | O2 % | Presión kPa | Gravedad | Fuente del centro |
|---|---|---|---|---|
| Base lunar | 26.5–34 | 56.5–70.3 | parcial | 8.2 psia/34 % y 10.2 psia/26.5 % (NTRS 20220005709, 20240005117); Luna ≈ 0.16 g (NASA/TM-1998-207417) |
| Traje espacial | 85–100 | 25–35 | cualquiera | 4.3 psia ≈ 29.6 kPa y 85 % O2 (NTRS 20240005151, 20220016245) |
| ISS / Tierra | 19–23 | 95–105 | cualquiera | 21 % O2 y 14.7 psia = 101.35 kPa (NTRS 20240005117) |

- La gravedad **no entra a la relevancia** **[Supuesto del equipo]**: casi todos los experimentos son
  de microgravedad y todo daría 0. Se reporta aparte: `scenario_counts` distingue «hay ensayos con
  esta atmósfera» de «además en la gravedad del escenario». Así sale el vacío «0 ensayos en
  gravedad parcial».
- Dónde está la evidencia de que en gravedad parcial el fuego puede comportarse distinto
  [Fuente]: Friedman, NASA/TM-1998-207417, y Takahashi y Linteris, NASA/CP-2001-210826.

## Gravedad (`gravity_counts`)
`gravity_level` debe venir **en g** (1 = Tierra). Categorías: microgravedad (g < 0.01), parcial
(0.01 ≤ g < 0.9), normal (0.9 ≤ g ≤ 2). **Los umbrales son [Supuesto del equipo].** El texto
(«microgravity», «lunar», «1 g», …) también se reconoce. Lo que no encaja queda en «sin
clasificar» (visible), y lo vacío en «sin dato». Un 0 en «parcial» es un vacío real.

## Fuentes (NTRS = ntrs.nasa.gov/api/citations/<número>)
- 20240005117 — ICES-2024-128: atmósfera de exploración 8.2 psia (56.54 kPa)/34 % O2; 14.7 psia (101.35 kPa)/21 %.
- 20220005709 — AsMA 2022, Abercromby: 8.2 psi/34 % recomendada (EAWG, NASA/TP-2010-216134); 10.2 psi/26.5 %.
- 20220016245 — AsMA 2022: 56.5 kPa, 34 % O2; EVA a 29.6 kPa.
- 20240005151 — Garbino 2024: EVA simulada a 4.3 psia, 85 % O2.
- 20220015741 — menor presión exige más O2, lo que puede aumentar el riesgo de incendio.
- 19980209743 — NASA/TM-1998-207417, Friedman: 0.38 g en Marte, 0.16 g en la Luna; gravedad parcial.
- Takahashi y Linteris, NASA/CP-2001-210826: la tasa máxima de propagación en papel fino ocurrió en gravedad marciana.

## Para Dev A
- `rank` y `rank_scenario` no reordenan ni reinician el índice: ordena por `score_total` en la app.
- Evidencia y cobertura son relativas a la tabla recibida: llama a `rank` con la tabla completa y
  **filtra después**.
- `coverage_grid(df)`: filas = presión, columnas = oxígeno, en texto; 0 = vacío.