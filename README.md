# NASA Fire Dashboard

Dashboard de seguridad contra incendios en microgravedad (NASA Space Apps 2026).

## Requisitos

- Python 3.10 o superior.

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

- `data/processed/master_table.csv`: mismas columnas que `data/mock/master_table_mock.csv` (Python 1).
- `src/ranking.py`: `rank(df, weights) -> df` con `score_relevancia`, `score_riesgo`,
  `score_evidencia`, `score_cobertura`, `score_total` (Python 2).
- `src/coverage.py`: `coverage_grid(df) -> DataFrame` (filas: bins de presión, columnas: bins de O2, valores: conteo).
- `data/processed/insights.json`: formato definido en `src/llm/schemas.py` (Python 3).
  `data/mock/insights_mock.json` es solo un ejemplo provisional de la app.

La app nunca llama al LLM: solo lee JSON precalculado.
