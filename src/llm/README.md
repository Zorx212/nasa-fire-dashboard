# Capa LLM (Python 3)

Convierte los PDF de las investigaciones PSI de la NASA en **insights con citas verificables**.
Esta carpeta documenta solo la capa LLM; la app (`app/`), el ranking y las tablas son de otros módulos.

**Flujo:** PDF → texto por página → extracción con LLM → verificación de citas → `data/processed/insights.json`.
La app nunca llama al LLM: solo lee JSON ya calculado, así que el demo funciona sin internet ni clave.

## Estado de las piezas

| Pieza | Archivo | Estado |
|---|---|---|
| Configuración (modelo y clave) | `src/config.py` | En `main` |
| Rutas del proyecto | `src/paths.py` | En `main` (`CACHE_DIR` llega con la caché) |
| Texto de los PDF | `src/pdf_text.py` | En `main` |
| Contrato de `insights.json` | `src/llm/schemas.py` | En `main` (oficial, global) |
| Caché de respuestas | `src/llm/cache.py` | PR #4 en revisión |
| Catálogo y verificador de citas | `src/catalog.py`, `src/llm/verify.py` | En preparación; se documenta al abrir su PR |
| Cliente de la API, prompts y coordinador | `src/llm/client.py`, `src/llm/prompts.py`, `src/llm_extract.py` | Pendiente |

## Configuración

Requiere Python 3.10 o superior. Las variables viven en un archivo `.env` local (no se sube a Git); la plantilla es `.env.example`.

| Variable | Para qué | Valor por defecto |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Anthropic. Solo se pide al llamar a la API | ninguno |
| `LLM_MODEL` | Modelo que se usa | `claude-sonnet-5-5` |

- `src/config.py` es el único lugar que lee estas variables: `LLM_MODEL` y `get_api_key()`. Importar el módulo **no** exige la clave; `get_api_key()` lanza `RuntimeError` con un mensaje claro si falta.
- `src/paths.py` es el único lugar que define rutas: `PROJECT_ROOT`, `RAW_DIR` (`data/raw`) y `TEXT_DIR` (`data/text`). Ningún otro archivo repite rutas ni valores de configuración.

## Texto de los PDF (`src/pdf_text.py`)

Los PDF originales van en `data/raw/` (no se suben a Git). Cada archivo se llama `PSI-<n>-<descripción>.pdf`, por ejemplo `PSI-107-SPICE-FinalReport.pdf`: el `psi_id` sale del nombre y no se pasa por argumento. Un nombre que no empiece con `PSI-`, dígitos y luego fin de nombre, `_`, `-`, `.` o espacio (por ejemplo, `PSI-107abc.pdf`) da `ValueError`.

```bash
python -m src.pdf_text data/raw/PSI-107-SPICE-FinalReport.pdf
```

Escribe `data/text/<psi_id>/<nombre del PDF sin extensión>.json` (si ya existe, lo sobrescribe y avisa) e imprime un resumen: PSI, páginas, páginas vacías y los primeros 300 caracteres.

Formato del JSON, un archivo por PDF:

```json
{
  "psi_id": "PSI-107",
  "filename": "PSI-107-SPICE-FinalReport.pdf",
  "pages": [
    { "page_number": 1, "text": "…", "is_empty": false }
  ]
}
```

- `page_number` empieza en 1 y es la **posición de la página en el PDF**, no el número impreso (la portada de PSI-107 lleva «i»). Esa es la unidad de cita.
- `text` es el texto **crudo** de pymupdf: no se normaliza al guardarlo. La normalización se hace solo al verificar citas.
- `is_empty` es `true` si la página no tiene texto (por ejemplo, solo imágenes).
- El JSON no lleva DOI. El DOI sale del catálogo, nunca del LLM.

Ejemplo versionado: `data/text/PSI-107/PSI-107-SPICE-FinalReport.json` (28 páginas, ninguna vacía).

## Contrato de `insights.json` (`src/llm/schemas.py`)

Es el contrato global y oficial entre la capa LLM y la app. **No se edita**: cualquier cambio lo decide el equipo, no esta capa. Los modelos son Pydantic 2 con `extra="forbid"` (un campo desconocido es error).

**`InsightsDocument`** (raíz del archivo)

| Campo | Tipo | Regla |
|---|---|---|
| `generated_at` | fecha y hora | ISO 8601; se espera con zona horaria |
| `model` | texto | no vacío |
| `prompt_version` | texto | no vacío |
| `insights` | lista de `Insight` | al menos 1 |

**`Insight`**

| Campo | Tipo | Regla |
|---|---|---|
| `title` | texto | no vacío |
| `description` | texto | no vacío |
| `evidence_status` | `"supported"` \| `"insufficient_data"` | obligatorio |
| `confidence` | `"high"` \| `"medium"` \| `"low"` \| `null` | ver reglas abajo |
| `citations` | lista de `Citation` | ver reglas abajo |
| `explanation` | texto | no vacío |

**`Citation`**

| Campo | Tipo | Regla |
|---|---|---|
| `psi_id` | texto | no vacío, por ejemplo `PSI-107` |
| `doi` | texto \| `null` | opcional |
| `page` | entero | mayor que 0; posición en el PDF |
| `quote` | texto | no vacío; texto literal de esa página |

**Reglas de coherencia** (las aplica el validador de `Insight`):

- `supported` exige al menos una cita y un nivel de `confidence`.
- `insufficient_data` no puede traer citas y exige `confidence: null` (se usa cuando la evidencia no alcanza: «no hay datos suficientes»).

**Qué el esquema NO comprueba:** que la cita exista de verdad en el PDF, que el `psi_id` esté en el catálogo, que la página esté en rango ni que haya DOI. Eso lo cubren el verificador, el catálogo y el coordinador.

Ejemplo (datos falsos, `PSI-000`, marcados `EXAMPLE DATA`): `data/processed/insights.sample.json`. El archivo real será `data/processed/insights.json`. Para validar un archivo:

```bash
python -c "from pathlib import Path; from src.llm.schemas import InsightsDocument as D; D.model_validate_json(Path('data/processed/insights.sample.json').read_text(encoding='utf-8')); print('ok')"
```

`data/mock/insights_mock.json` es un ejemplo provisional de la app y **no** sigue este esquema.

## Caché de respuestas (`src/llm/cache.py`)

Guarda en disco las respuestas reales del LLM para repetir una extracción sin volver a llamar a la API (que cuesta) y para que el demo funcione sin internet ni clave. Leer la caché no exige clave.

- `build_cache_key(request: dict) -> str`: huella SHA-256, en hexadecimal, de `json.dumps(request, sort_keys=True, ensure_ascii=False, separators=(",", ":"))` en UTF-8. `request` debe ser **exactamente** lo que se envía a la API (modelo, `max_tokens`, `temperature`, system, messages). Cambiar cualquier carácter del prompt cambia la huella.
  - El tipo importa: `temperature` `0` y `0.0` producen huellas distintas. Quien llama debe usar siempre el mismo tipo.
- `get_cached_response(key, cache_dir) -> dict | None`: devuelve la entrada guardada o `None` si no existe (*miss*). Un archivo corrupto (JSON inválido o ilegible) o que no es un diccionario se avisa por consola y se trata como *miss*.
- `save_cached_response(key, cache_dir, entry) -> Path`: crea la carpeta si falta y escribe `<key>.json` (UTF-8, `ensure_ascii=False`, `indent=2`). Devuelve la ruta.
- `cache_dir` siempre llega por parámetro; `cache.py` no importa `config.py` ni `paths.py`. La carpeta real es `CACHE_DIR` en `src/paths.py` (`data/cache/llm`).
- Solo se guardan salidas reales del LLM, nunca datos ficticios. La caché no agrega metadatos: quien llama (el cliente de la API) decide qué lleva `entry`, por ejemplo modelo y fecha.

## Convenciones de la capa

**Arquitectura**
- Modular y con responsabilidad única: un archivo, una responsabilidad. No hay archivos monolíticos.
- Configuración centralizada: modelo y clave en `config.py`, rutas en `paths.py`. Nada hardcodeado en otros archivos.
- Solo `client.py` (pendiente) conocerá al proveedor de la API. `cache.py` y `verify.py` reciben lo que necesitan por parámetro.
- Estructura: `src/llm/` (esquemas, caché, cliente, prompts, verificador), `tests/`, `data/raw/` (PDF, no se suben), `data/text/` (texto extraído), `data/processed/` (`insights.json` y ejemplo), `data/cache/llm/` (respuestas del LLM).

**Código**
- Anotaciones de tipo (`str | None`), funciones pequeñas con una sola tarea y docstring breve (qué hace y qué devuelve).
- Errores claros y accionables (`ValueError`, `RuntimeError`); sin `except` vacíos; sin `print` de depuración.
- Ningún módulo exige la clave al importarse.
- Identificadores, comentarios y docstrings en inglés; esta documentación, en español.

**Secretos**
- La clave vive solo en `.env`. Nunca en código, logs, caché, documentación ni commits.

**Pruebas**
- Se corren desde la raíz con `python -m pytest tests -q` (así `src` es importable). `pytest` entra a `requirements.txt` con el PR de la caché.
- Pasan **sin clave y sin internet**: usan `tmp_path` y datos de `data/text/PSI-107/`.
- Ninguna prueba automática llama a la API. Una prueba con la API real es manual, con aprobación expresa, con el modelo más barato y con `max_tokens` mínimo.

**Git**
- Commits atómicos en inglés, con Conventional Commits (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`): un cambio lógico por commit.
- Una rama por unidad, desde `main` actualizado. `git add` con rutas exactas; nunca `git add .`.
- Los PR van en español (qué, por qué, cómo probar) y los revisa otra persona. Nada se sube a `main` directamente.

## Reglas del contrato (no negociables)

1. `src/llm/schemas.py` no se modifica desde esta capa.
2. El LLM no escribe el DOI: sale de `data/catalog.csv`.
3. El texto del PDF se guarda crudo; solo se normaliza al verificar citas.
4. La caché guarda solo salidas reales del LLM.
5. Una cita sin verificar no llega al dashboard.
6. Sin evidencia suficiente, el insight es `insufficient_data` («no hay datos suficientes»).
7. El demo funciona sin internet.
8. Los PDF se llaman `PSI-<n>-<descripción>.pdf`.
9. Ninguna clave en el repositorio.

## Glosario

- **PSI**: identificador de una investigación (por ejemplo `PSI-107`, SPICE).
- **DOI**: identificador permanente de la publicación; se toma del catálogo.
- **Insight**: conclusión del LLM sobre uno o varios documentos, con su evidencia.
- **Cita**: fragmento literal de una página de un PDF que respalda un insight.
- **Huella (clave de caché)**: SHA-256 de la petición exacta; da el nombre del archivo en la caché.
- ***Hit* / *miss***: la respuesta sí / no estaba en la caché.
- **Pydantic**: biblioteca que valida la forma de los datos; `extra="forbid"` rechaza campos desconocidos.
