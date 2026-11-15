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


## Regenerar la tabla maestra

Los CSV y PDFs originales no están en Git: viven en la carpeta `data-raw` del Drive del equipo:(https://drive.google.com/drive/folders/1NO1EmH_un1YWHiUuS2RPZqDvNYCIrrBV)

1. Descarga esa carpeta y colócala en `data/raw/`, con una subcarpeta por investigación (`PSI_39`, `PSI_99`, `PSI_101`, ...).
2. Con el entorno virtual activo: `pip install -r requirements.txt`
3. Desde la raíz del proyecto:

```bash
python -m src.normalize
```

Resultado: `data/processed/master_table.csv`. La salida imprime las filas por PSI, los avisos y `[ok] columnas idénticas al mock`.

- Entradas: `data/raw/PSI_<n>/*.csv` y `data/catalog.csv` (doi, license, title).
- Para agregar una investigación: una entrada nueva en `SPECS` de `src/normalize.py`; la llave es la ruta del CSV dentro de `data/raw`.
- Convenciones: `gravity_level` 0 (en g), `material_type` gas / sólido / líquido, vacío = sin dato. Conversiones y pendientes en `notes/discoveries.md`.
