# ELIA — Documentación para desarrollo y despliegue

## Entorno virtual (Python)

Desde la raíz del repositorio:

```text
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
```

- **Excel → BDD** requiere `pandas`, `python-calamine` y `openpyxl` (incluidos en `requirements.txt`). Si ves `pandas no está instalado`, reinstala dependencias: `pip install -r requirements.txt`.
- Activar después: `.venv\Scripts\activate` (Windows) o `source .venv/bin/activate` (Linux/macOS).
- Ejecutar la app: `python main.py`

## Node.js en `core/node` (grabación con Puppeteer)

El repositorio solo incluye `package.json` / `package-lock.json`. Genera el runtime en tu máquina:

```text
cd core/node
npm install
```

Necesitas Node.js 16+ en el PATH o una copia portable con `node.exe` bajo `core/node/`. PyInstaller empaqueta `core/node` tal como esté en el disco al construir el `.exe`.

## Frontend (React / Vite)

Tras cambiar la UI web:

```text
cd frontend
npm install
npm run build
```

La salida queda en `frontend/dist/` (la sirve FastAPI en modo web).

## Build de release (Cython + JS + PyInstaller)

Desde la raíz del repo (con el venv activado y herramientas de compilación instaladas según tu SO):

```
python scripts/build_release.py --cython
```

- `--cython` compila los módulos listados en `core/_cython_build_manifest.py` antes del empaquetado.
- Sin `--cython`: ofuscación JS (si aplica) y PyInstaller según `ELIA.spec`.
- Revisa `scripts/build_release.py` para flags del ofuscador de `recorder.js`.

Luego, si usas solo PyInstaller:

```text
python -m PyInstaller --noconfirm ELIA.spec
```

## Licencia offline (`core/elia_license.py`)

- **Demostración:** período limitado desde el primer arranque; estado en datos de usuario (p. ej. `%LOCALAPPDATA%\ELIA\` en Windows).
- **Activación con clave:** Configuración (⚙) en la UI web, o variable de entorno `ELIA_ACTIVATION_KEY=<clave>` antes de arrancar.
- El estado en `%LOCALAPPDATA%\\ELIA\\license_state.json` guarda la clave (`saved_activation_key`) y se **revalida con HMAC en cada arranque**; editar solo `"activated": true` no concede licencia.
- **Generar clave para una huella** (`scripts/generate_license_key.py`; el secreto `_LICENSE_SEED` debe coincidir con el build):
  - `python scripts/generate_license_key.py --machine <huella32hex>` — permanente, sin módulos extra
  - `--duration 15d` — 15 días (extensión demo); `30d` — 1 mes; `365d` — 1 año; `perm` — permanente
  - `--mobile` / `--legacy` — incluir grabación móvil o legacy en la licencia
  - Ejemplo: `python scripts/generate_license_key.py --machine <huella> --duration 30d --mobile --legacy`
- **Solo desarrollo:** `ELIA_SKIP_LICENSE=1` omite comprobaciones y **habilita todos los módulos** (móvil, legacy, doc_to_bdd). No usar en entregas.
- Tras cambiar `elia_license.py` o `modules_config.py`, recompila Cython (`python setup_cython.py build_ext --inplace`) para que el `.pyd` no quede desactualizado.

## Kill switch (desactivación local, sin red)

Según la implementación en `elia_license.py`, la aplicación puede negarse a arrancar si existen archivos locales concretos (por ejemplo en `%LOCALAPPDATA%\ELIA\` o junto al ejecutable). Consulta las rutas exactas en `kill_switch_active()` antes de documentar a clientes.

## Datos de usuario y proyectos

Los proyectos generados suelen ir bajo **Documentos/ELIA** (Windows). Variable opcional: **`ELIA_USER_DATA`** (ruta raíz de datos). La memoria local de correcciones BDD (few-shot para IA) se guarda en **`elia_memory.json`** en esa misma área (`core/elia_memory.py`).

## Integraciones (Jira, Value Edge, Gherkin)

Módulos Python en la raíz del paquete **`core/`** (mismo nivel que los demás conversores y utilidades): **`jira_extractor.py`**, **`value_edge_extractor.py`**, **`gherkin_converter.py`**, **`integrations_config_loader.py`**, **`connectors_profiles_store.py`**, **`integrations_service.py`**.

- **Configuración recomendada:** `{ELIA_USER_DATA}/external_connectors/secrets.ini` con secciones `[JIRA]` (`URL`, `EMAIL`, `API_TOKEN`) y `[ValueEdge]` (`URL`, `SHARED_SPACE`, `WORKSPACE`, `TECH_PREVIEW_FLAG`, `USER`, `PASSWORD`, `LOGIN`). Si existía una instalación anterior con `.../elia/secrets.ini` bajo datos de usuario, ese archivo se sigue leyendo hasta migrar. Alternativa: **`ELIA_SECRETS_INI`** con ruta absoluta, o variables **`ELIA_*`** (p. ej. `ELIA_JIRA_URL`, `ELIA_VALUEEDGE_URL`; ver `integrations_config_loader.py`).
- **Uso programático:** `import core.integrations_service as integrations` — `get_jira_extractor()`, `get_value_edge_extractor()`, `run_gherkin_batch(...)`, etc.
- La carpeta histórica **`DICAI/`** quedó obsoleta; no la uses como punto de entrada.

## Modelo Gemma (GGUF, opcional)

Coloca el `.gguf` bajo `resources/models/gemma/` (los modelos grandes suelen estar en `.gitignore`). La resolución de ruta está en `core/gemma_model_paths.py`; inferencia con `llama-cpp-python` en `core/gemma_inference.py`. Variables útiles: `ELIA_LLAMA_N_CTX`, `ELIA_LLAMA_N_GPU_LAYERS`.

## Interfaz web (recordatorio para desarrollo)

Tras cambios en `frontend/`, ejecuta `npm run build` y prueba en `127.0.0.1`. La UI depende de `frontend/dist` empaquetado o generado localmente. Si no ves controles nuevos (p. ej. tema oscuro), casi siempre es que el `.exe` o `frontend/dist` no se regeneró tras el `git pull`.

Al cerrar la **pestaña de inicio**, el frontend llama a `POST /api/app/exit` y `main.py` hace polling de `GET /api/app/should-exit` para detener Uvicorn y salir del proceso (evita que la app quede en segundo plano sin consola).

## Ramas Git

Convención útil: `main`, `change_tests` y una rama de trabajo `cursor/...`. Elimina ramas fusionadas que ya no necesites en el remoto para mantener el repositorio claro.
