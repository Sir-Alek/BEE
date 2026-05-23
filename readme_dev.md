# ELIA — Documentación para desarrollo y despliegue

## Versión del producto (sincronizar en releases)

| Dónde | Qué editar |
|-------|------------|
| **Pestaña Acerca de** (UI) | `core/_version.py` → `ELIA_VERSION` |
| **Consola al arrancar** | Mismo `core/_version.py` (importado desde `main.py`) |
| **Instalador Windows** | `ELIA_Setup.iss` → `#define MyAppVersion` |

Edita **`core/_version.py`** (y sincroniza `ELIA_Setup.iss`). Esos módulos **no van a Cython**. Si existe un `core/version*.pyd` antiguo, cierra ELIA y bórralo (o ejecuta `build_release.py`, que intenta limpiarlo).

Tras cambiar la versión, reinicia ELIA en desarrollo; para el `.exe`, vuelve a ejecutar PyInstaller.

## Entorno virtual (Python)

Desde la raíz del repositorio:

```text
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
```

- **Excel → BDD** requiere `pandas`, `python-calamine` y `openpyxl` (incluidos en `requirements.txt`). Si ves `pandas no está instalado`, reinstala dependencias: `pip install -r requirements.txt`.
- **Grabación móvil (Appium)** y **legacy (escritorio Windows)** requieren los paquetes pip de `requirements.txt` (`Appium-Python-Client`, `pynput`, `pywinauto`, `pywin32`, `comtypes`). Tras `pip install -r requirements.txt`, reconstruye el `.exe` con `python scripts/build_release.py` para que PyInstaller los empaquete (imports lazy).
- Activar después: `.venv\Scripts\activate` (Windows) o `source .venv/bin/activate` (Linux/macOS).
- Ejecutar la app: `python main.py`
- Usa siempre el **venv del repo** (`.venv\Scripts\activate`). Si ejecutas `python main.py` con el Python global de Windows, faltarán paquetes como `python-multipart` y la UI web no arrancará.

## Inteligencia local (Gemma) — política por defecto

- **Marca:** Evolving Learning & Intelligent Automation (ELIA).
- **Modo por defecto:** `auto` en `%LOCALAPPDATA%\ELIA\ai_preferences.json` (o datos de usuario vía `ELIA_USER_DATA`).
  - **auto:** IA activa si el modelo GGUF existe, `llama-cpp-python` está disponible y hay **≥ 8 GB RAM total** y **≥ 4 GB libres**.
  - **on:** fuerza IA en cada job.
  - **off:** modo rápido / heurístico (sin Gemma).
- Los jobs **ignoran** `use_ai` enviado por el frontend; el servidor resuelve la política en cada `POST /api/jobs/convert`.
- Variables opcionales: `ELIA_AI_MIN_RAM_GB`, `ELIA_AI_MIN_RAM_FREE_GB`, `ELIA_USE_AI` (override 0/1), `ELIA_ALLOW_CHROMIUM_FALLBACK` (solo grabador Chrome).
- API: `GET /api/ai/capabilities`, `PUT /api/ai/preferences` con `{ "mode": "auto"|"on"|"off" }`.

## Requisitos de grabación web (Windows)

- **Google Chrome** instalado (obligatorio). **Microsoft Edge no sustituye** a Chrome para la grabación Puppeteer.
- Si Chrome está en una ruta no estándar, defina antes de arrancar ELIA:
  - `ELIA_CHROME_PATH=C:\ruta\completa\chrome.exe` (también acepta `CHROME_PATH` o `ELIA_BROWSER_PATH`).
- **Chromium empaquetado (Puppeteer)** solo como respaldo técnico, no como requisito de usuario:
  - `ELIA_ALLOW_CHROMIUM_FALLBACK=1` y `cd core\node && npm install` (debe existir el Chromium descargado por puppeteer).
- Diagnóstico: `python scripts/diagnose_recorder_env.py`

## Requisitos de grabación móvil (Appium)

- **Paquetes pip** (incluidos en `requirements.txt`): `Appium-Python-Client` (depende de `selenium`, ya listado).
- **Fuera de pip** (instalar en el PC de desarrollo/pruebas):
  1. Node.js + Appium Server: `npm install -g appium`
  2. Driver Android: `appium driver install uiautomator2`
  3. Android SDK / platform-tools con `adb` en PATH
  4. Servidor en marcha: `appium` (puerto **4723**)
  5. Dispositivo visible: `adb devices`
- Si el job falla con *Appium-Python-Client no instalado*:
  - **Desarrollo:** activa `.venv` y `pip install -r requirements.txt`; arranca con `.venv\Scripts\python.exe main.py` (no el Python global).
  - **Ejecutable:** reinstala deps en el venv de build y vuelve a ejecutar `python scripts/build_release.py`.

## Requisitos de grabación legacy (Windows)

- **Paquetes pip:** `pynput`, `pywinauto`, `pywin32`, `comtypes` (incluidos en `requirements.txt`).
- Sin `pynput`, la grabación cae a un modo básico con PyAutoGUI (posición del cursor cada 2 s).
- `pywinauto` enriquece clicks con nombre/tipo de control UIA (opcional en runtime, recomendado).

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

`npm run build` ejecuta `tsc --noEmit` y después empaqueta con Vite. Para solo verificar tipos: `npm run typecheck`.

La salida queda en `frontend/dist/` (la sirve FastAPI en modo web).

### Estructura del frontend (desde 0.7.0)

| Ruta | Rol |
|------|-----|
| `frontend/src/App.tsx` | Estado global, efectos y composición |
| `frontend/src/home/HomeSurface.tsx` | Pestañas UI Automation e Inteligencia de Requerimientos |
| `frontend/src/job/JobWorkspace.tsx` | Prompts, progreso y resultados del job |
| `frontend/src/settings/SettingsDialog.tsx` | Modal de configuración |
| `frontend/src/layout/AppShell.tsx` | Cabecera y alertas |
| `frontend/src/app/` | Constantes, licencia, utilidades |
| `frontend/src/recording/` | Formularios tipados Web/Móvil/Legacy |

## Build de release (Cython + JS + PyInstaller)

Desde la raíz del repo (con el venv activado y herramientas de compilación instaladas según tu SO):

```
python scripts/build_release.py
```

- Por defecto: **Cython** (todos los `.py` bajo `core/` salvo `__init__.py`) + ofuscación JS + PyInstaller + retirada de `.py` duplicados en `dist/ELIA/_internal/core/`.
- El manifiesto se **autodescubre** en `core/_cython_build_manifest.py` (no hace falta listar módulos a mano).
- `--no-cython`: solo para depuración local; el `.exe` llevará fuentes `.py` de core.
- `--no-strip-py`: no borra `.py` del dist tras PyInstaller (depuración).
- Revisa `scripts/build_release.py` para flags del ofuscador de `web_capture_engine.js`.

Luego, si usas solo PyInstaller:

```text
python -m PyInstaller --noconfirm ELIA.spec
```

## Licencia offline (`core/elia_license.py`)

- **Activación obligatoria:** sin licencia vigente no se ejecutan jobs (grabación, conversión, `doc_to_bdd`, conectores, IA). La app arranca para ver la pantalla principal y usar Configuración → **General** (tema), **Licencia** y **Acerca de**.
- **Módulos:** `mobile_recording` y `legacy_recording` vienen **solo** de la clave activa (flags `M`/`L`). `doc_to_bdd` requiere licencia vigente. Las claves de módulo individuales no tienen efecto en producción.
- **Huella de equipo:** `get_machine_fingerprint()` usa hardware estable (Windows: `wmic` baseboard/cpu/csproduct + MAC); **no** usa el nombre del equipo, para sobrevivir a reinstalar Windows.
- **Estado:** `%LOCALAPPDATA%\ELIA\license_state.json` + respaldos de comodidad firmados (HMAC) con la clave. Borrar el JSON restaura desde respaldo si existe; borrar todo exige volver a introducir la clave.
- **Activación:** UI web, o `ELIA_ACTIVATION_KEY=<clave>` antes de arrancar. Se **revalida HMAC en cada arranque**; editar solo `"activated": true` no concede licencia.
- **Huella en el PC del usuario (soporte):** `python scripts/show_machine_fingerprint.py` (no requiere `ELIA_SKIP_LICENSE` ni licencia activa).
- **Formato de clave v2:** `ELIA-{dur}-{mods}-{issue_ts}-{hmac64}` — el timestamp de emisión va en la clave y en el HMAC; la caducidad no depende de `activated_ts` en JSON.
- **Claves v1** (`ELIA-{dur}-{mods}-{hmac64}` sin timestamp): legado; caducidad aún usa `activated_ts` del JSON. Reemitir con el generador actual.
- **Generar clave** (`scripts/generate_license_key.py`; `_LICENSE_SEED` debe coincidir con el build):
  - `python scripts/generate_license_key.py --machine <huella32hex>` — emite v2 con `issue_ts` = ahora
  - `--duration 15d|30d|365d|perm` — temporal o permanente
  - `--issue-ts <unix>` — solo pruebas (timestamp fijo)
  - `--mobile` / `--legacy` — incluir grabación móvil o legacy en la licencia
  - Ejemplo: `python scripts/generate_license_key.py --machine <huella> --duration 30d --mobile --legacy`
- **Solo desarrollo:** `ELIA_SKIP_LICENSE=1` omite comprobaciones y **habilita todos los módulos** (móvil, legacy, doc_to_bdd). No usar en entregas.
- Tras cambiar `elia_license.py` o `modules_config.py`, recompila Cython (`python setup_cython.py build_ext --inplace`) para que el `.pyd` no quede desactualizado.

## Anti-downgrade local (`core/install_manifest.json`)

- **Runtime (HMAC):** al arrancar, `main.py` lee `%LOCALAPPDATA%\ELIA\install_manifest.json` (firmado). Si `ELIA_VERSION` es menor que `max_version` registrada, la app sale con código 3.
- **Instalador (semver):** `ELIA_Setup.iss` compara `{#MyAppVersion}` con `max_version` del manifest antes de instalar; aborta si el setup es más viejo.
- **Upgrade in-place:** `UsePreviousAppDir=yes` — instalar encima conserva licencia y datos en `Documents\ELIA`.
- **Desarrollo:** `ELIA_ALLOW_DOWNGRADE=1` permite ejecutar una versión inferior (no usar en entregas).
- El manifest se eleva en cada arranque exitoso con versión igual o superior (`record_version_if_newer`).

## Revocación y kill switch (soporte interno / desarrollo)

**Revocación suave** (app arranca; jobs bloqueados):

```text
python scripts/revoke_license.py
python scripts/revoke_license.py --keep-backups
ELIA_REVOKE_ON_START=1 python main.py
$env:ELIA_REVOKE_ON_START=1; python main.py    
```

**Kill switch duro** (app no arranca — `exit 2`). Crear uno de estos archivos:

| Ruta |
|------|
| `%LOCALAPPDATA%\ELIA\KILL` |
| `%LOCALAPPDATA%\ELIA\elia_revoked.flag` |
| `{carpeta de ELIA.exe}\elia.kill` |
| `{carpeta de ELIA.exe}\ELIA_KILL` |

Quitar el archivo para rehabilitar (salvo licencia caducada, que requiere nueva clave).

## Datos de usuario y proyectos

Los proyectos generados suelen ir bajo **Documentos/ELIA** (Windows). Variable opcional: **`ELIA_USER_DATA`** (ruta raíz de datos). La memoria local de correcciones BDD (few-shot para IA) se guarda cifrada en **`elia_memory.enc`** (`core/elia_memory.py`, Fernet + huella de máquina). Migración automática desde `elia_memory.json` legado (`.bak`). Export/import para equipos: Configuración → Inteligencia → *Compartir base de conocimiento* (archivo `.enc` cifrado con frase de equipo compartida; fusión o reemplazo).

## Integraciones (Jira, Value Edge, Gherkin)

Módulos Python en la raíz del paquete **`core/`** (mismo nivel que los demás conversores y utilidades): **`jira_story_fetcher.py`**, **`value_edge_story_fetcher.py`**, **`story_gherkin_builder.py`**, **`integrations_config_loader.py`**, **`connectors_profiles_store.py`**, **`integrations_service.py`**.

- **Configuración recomendada:** `{ELIA_USER_DATA}/external_connectors/secrets.ini` con secciones `[JIRA]` (`URL`, `EMAIL`, `API_TOKEN`) y `[ValueEdge]` (`URL`, `SHARED_SPACE`, `WORKSPACE`, `TECH_PREVIEW_FLAG`, `USER`, `PASSWORD`, `LOGIN`). Si existía una instalación anterior con `.../elia/secrets.ini` bajo datos de usuario, ese archivo se sigue leyendo hasta migrar. Alternativa: **`ELIA_SECRETS_INI`** con ruta absoluta, o variables **`ELIA_*`** (p. ej. `ELIA_JIRA_URL`, `ELIA_VALUEEDGE_URL`; ver `integrations_config_loader.py`).
- **Uso programático:** `import core.integrations_service as integrations` — `get_jira_extractor()`, `get_value_edge_extractor()`, `run_gherkin_batch(...)`, etc.
- La carpeta histórica **`DICAI/`** quedó obsoleta; no la uses como punto de entrada.

## Modelo Gemma (GGUF, opcional)

Coloca el `.gguf` bajo `resources/models/gemma/` (los modelos grandes suelen estar en `.gitignore`). La resolución de ruta está en `core/gemma_model_paths.py`; inferencia con `llama-cpp-python` en `core/gemma_inference.py`. Variables útiles: `ELIA_LLAMA_N_CTX`, `ELIA_LLAMA_N_GPU_LAYERS`.

## Interfaz web (recordatorio para desarrollo)

Tras cambios en `frontend/`, ejecuta `npm run build` y prueba en `127.0.0.1`. La UI depende de `frontend/dist` empaquetado o generado localmente. Si no ves controles nuevos (p. ej. tema oscuro), casi siempre es que el `.exe` o `frontend/dist` no se regeneró tras el `git pull`.

Al cerrar la **pestaña de inicio**, el frontend llama a `POST /api/app/exit` y `main.py` hace polling de `GET /api/app/should-exit` para detener Uvicorn y salir del proceso (evita que la app quede en segundo plano sin consola).

## Pruebas automatizadas

Unitarias, API, integración (smoke Puppeteer, Jira/VE opt-in, nightly Appium/Legacy) y E2E Playwright están bajo **`tests/`**. Comandos rápidos desde la raíz: `npm test`, `npm run test:integration`, `npm run test:e2e`.

Documentación completa: **[tests/readme_tests.md](tests/readme_tests.md)**.

## Ramas Git

Convención útil: `main`, `change_tests` y una rama de trabajo `cursor/...`. Elimina ramas fusionadas que ya no necesites en el remoto para mantener el repositorio claro.
