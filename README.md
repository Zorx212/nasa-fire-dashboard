# nasa-fire-dashboard

Dashboard de seguridad contra incendios en microgravedad (NASA Space Apps 2026).

## Ejecutar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
streamlit run app/app.py
```

La app lee `data/processed/master_table.csv` e `insights.json`. Si no existen,
usa los datos de ejemplo de `data/mock/` y muestra un aviso.

## Contratos entre módulos

- `data/processed/master_table.csv`: columnas de la sección 8 del plan (Python 1).
- `src/ranking.py`: `rank(df, weights) -> df` con `score_relevancia`, `score_riesgo`,
  `score_evidencia`, `score_cobertura`, `score_total` (Python 2).
- `src/coverage.py`: `coverage_grid(df) -> DataFrame` (filas: bins de presión, columnas: bins de O2, valores: conteo).
- `data/processed/insights.json`: ver `data/mock/insights_mock.json` (Python 3).

La app nunca llama al LLM: solo lee JSON precalculado.
