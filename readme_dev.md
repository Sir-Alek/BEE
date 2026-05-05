# BEE — Documentación para desarrollo y despliegue

## Entorno virtual (Python)

Desde la raíz del repositorio:

```text
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
```

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

```text
python scripts/build_release.py --cython
```

- `--cython` compila los módulos listados en `core/_cython_build_manifest.py` antes del empaquetado.
- Sin `--cython`: ofuscación JS (si aplica) y PyInstaller según `BEE.spec`.
- Revisa `scripts/build_release.py` para flags del ofuscador de `recorder.js`.

Luego, si usas solo PyInstaller:

```text
python -m PyInstaller --noconfirm BEE.spec
```

## Licencia offline (cuando exista `core/bee_license.py`)

- **Demostración:** período limitado desde el primer arranque; estado en datos de usuario (p. ej. `%LOCALAPPDATA%\BEE\` en Windows).
- **Activación con clave:** pantalla de inicio de la UI web, o variable de entorno `BEE_ACTIVATION_KEY=<clave>` antes de arrancar.
- **Generar clave para una huella:** si el repo incluye `scripts/generate_license_key.py`, úsalo con la huella mostrada en la UI (el secreto `_LICENSE_SEED` en `bee_license.py` debe coincidir con el build que distribuyes).
- **Solo desarrollo:** `BEE_SKIP_LICENSE=1` omite comprobaciones (no usar en entregas).

## Kill switch (desactivación local, sin red)

Según la implementación en `bee_license.py`, la aplicación puede negarse a arrancar si existen archivos locales concretos (por ejemplo en `%LOCALAPPDATA%\BEE\` o junto al ejecutable). Consulta las rutas exactas en el código de `kill_switch_active()` / `bee_license` de tu rama antes de documentar a clientes.

## Datos de usuario y proyectos

Los proyectos generados suelen ir bajo **Documentos/BEE** (Windows). Variable opcional: **`BEE_USER_DATA`** (ruta raíz de datos). La memoria local de correcciones BDD (few-shot para IA) puede guardarse en `bee_memory.json` en esa misma área, según la implementación de la rama.

## ELIA (Evolving Learning & Intelligent Automation)

Módulo en el paquete `elia/`: integración con **Jira** (API REST), **Value Edge / ALM Octane** y conversión **Gherkin** por lotes (clase `UltimateGherkinConverter`), pensada para orquestarse desde la UI web de BEE.

- **Configuración:** archivo recomendado `{BEE_USER_DATA}/elia/secrets.ini` (p. ej. `Documentos/BEE/elia/secrets.ini`) con secciones `[JIRA]` (`URL`, `EMAIL`, `API_TOKEN`) y `[ValueEdge]` (`URL`, `SHARED_SPACE`, `WORKSPACE`, `TECH_PREVIEW_FLAG`, `USER`, `PASSWORD`, `LOGIN`). Alternativa: variable **`ELIA_SECRETS_INI`** con ruta absoluta a otro `secrets.ini`, o variables de entorno con prefijo **`ELIA_`** (p. ej. `ELIA_JIRA_URL`, `ELIA_VALUEEDGE_URL`, etc.; ver `elia/config_loader.py`).
- **Uso programático:** `from elia import service` — `get_jira_extractor()`, `get_value_edge_extractor()`, `run_gherkin_batch(...)`, `jira_smoke_test()` / `value_edge_smoke_test()`.
- La carpeta histórica **`DICAI/`** en el repo quedó obsoleta frente a `elia/`; no la uses como punto de entrada.

## Modelo Gemma (GGUF, opcional)

Coloca el `.gguf` bajo `resources/models/gemma/` (los modelos grandes suelen estar en `.gitignore`). La resolución de ruta está en `core/gemma_model_paths.py`; inferencia con `llama-cpp-python` en `core/gemma_inference.py`. Variables útiles: `BEE_LLAMA_N_CTX`, `BEE_LLAMA_N_GPU_LAYERS`.

## Interfaz web (recordatorio para desarrollo)

Tras cambios en `frontend/`, ejecuta `npm run build` y prueba en `127.0.0.1`. La UI depende de `frontend/dist` empaquetado o generado localmente. Si no ves controles nuevos (p. ej. tema oscuro), casi siempre es que el `.exe` o `frontend/dist` no se regeneró tras el `git pull`.

Al cerrar la **pestaña de inicio**, el frontend llama a `POST /api/app/exit` y `main.py` hace polling de `GET /api/app/should-exit` para detener Uvicorn y salir del proceso (evita que `BEE.exe` quede en segundo plano sin consola).

## Ramas Git

Convención útil: `main`, `change_tests` y una rama de trabajo `cursor/...`. Elimina ramas fusionadas que ya no necesites en el remoto para mantener el repositorio claro.
