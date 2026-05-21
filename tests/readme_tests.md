# ELIA — Guía de pruebas

Toda la automatización (unitarias, API, integración y E2E) vive bajo `tests/`.

## Estructura

```
tests/
├── readme_tests.md          ← este documento
├── paths.py                 # REPO_ROOT compartido
├── run_all.py               # unit + api (unittest)
├── run_integration.py       # integración / smoke / nightly
├── support/
│   ├── recorder_stub.py     # stub de recorder.js (sin Chrome real)
│   └── markers.py           # flags ELIA_RUN_INTEGRATION / ELIA_RUN_NIGHTLY
├── fixtures/
│   └── stub_recorder.js     # script Node mínimo (BROWSER_READY)
├── unit/                    # test_*.py — lógica de dominio
├── api/                     # FastAPI (security, jobs, license, AI)
├── integration/             # smoke CI + opt-in red real + nightly
│   ├── test_puppeteer_smoke.py
│   ├── test_connectors_live.py
│   ├── test_legacy_runtime.py
│   └── test_appium_runtime.py
└── e2e/                     # Playwright (UI)
    ├── playwright.config.ts
    ├── package.json
    ├── specs/               # *.spec.ts
    ├── pages/               # Page Objects
    ├── fixtures/
    ├── helpers/
    └── scripts/             # e2e_serve.py, licencia E2E
```

## Requisitos

- Python 3.10.x y `.venv` con `pip install -r requirements.txt`
- Node.js 20+ (solo para E2E)
- Windows (grabador web/legacy; CI también usa `windows-latest`)

---

## Ejecutar suites

Desde la **raíz del repo**:

```powershell
# Unitarias + API (107 tests)
npm test
# equivalente:
.venv\Scripts\python.exe tests\run_all.py

# Integración — smoke Puppeteer (CI por defecto)
npm run test:integration
# equivalente:
.venv\Scripts\python.exe tests\run_integration.py

# E2E Playwright (14 tests)
npm run test:e2e
# equivalente:
cd tests\e2e
npm run test:e2e
```

---

## Suites Python

### `unit/` — unitarias

Licencia, módulos, BDD, ingestión de documentos, legacy/mobile/web (capacidades), integraciones con mocks, etc.

No requieren servidor ni red.

### `api/` — FastAPI

Ciclo de vida de jobs, licencia, seguridad (`_require_localhost`, path traversal), preferencias AI.

Usan `TestClient` + fixtures en `tests/api/support.py` (`elia_test_app`, `EliaApiActor`).

Cada test aísla licencia y datos de usuario (`ELIA_USER_DATA` temporal) para no tocar `Documents/ELIA` del desarrollador.

### `integration/` — smoke e integración

| Archivo | Cuándo corre | Qué valida |
|---------|--------------|------------|
| `test_puppeteer_smoke.py` | **Siempre** (`run_integration.py`) | Job `puppeteer_recorder` vía API con stub; `stub_recorder.js` con Node |
| `test_connectors_live.py` | `ELIA_RUN_INTEGRATION=1` | Jira / Value Edge con red real |
| `test_legacy_runtime.py` | `ELIA_RUN_NIGHTLY=1` | Ventana Notepad, flujo legacy en Windows |
| `test_appium_runtime.py` | `ELIA_RUN_NIGHTLY=1` | Servidor Appium accesible + cliente Python |

---

## Integración Jira / Value Edge (opt-in)

No se ejecuta en CI local ni en el job principal. Actívala solo cuando tengas credenciales válidas:

```powershell
$env:ELIA_RUN_INTEGRATION = "1"

# Jira
$env:ELIA_JIRA_URL = "https://tu-jira.example.com"
$env:ELIA_JIRA_EMAIL = "qa@example.com"
$env:ELIA_JIRA_TOKEN = "token-api"

# Value Edge
$env:ELIA_VE_URL = "https://ve.example.com"
$env:ELIA_VE_SHARED_SPACE = "space1"
$env:ELIA_VE_WORKSPACE = "ws1"
$env:ELIA_VE_USER = "usuario"
$env:ELIA_VE_PASSWORD = "contraseña"
# opcional:
$env:ELIA_VE_LOGIN = "https://ve.example.com/authentication/sign_in"
$env:ELIA_VE_TECH_PREVIEW = "true"

python tests\run_integration.py
```

En GitHub Actions: job `integration-live` + secrets `ELIA_JIRA_*` y `ELIA_VE_*`.

---

## Nightly — Appium / Legacy runtime

Requiere entorno Windows real (y Appium en marcha para los tests móviles):

```powershell
$env:ELIA_RUN_NIGHTLY = "1"
$env:ELIA_APPIUM_URL = "http://127.0.0.1:4723"   # opcional

python tests\run_integration.py
```

- **Legacy:** lanza `notepad.exe` y comprueba detección de ventana; flujo de grabación acortado con `should_stop_recording`.
- **Appium:** comprueba `GET /status` y que el cliente Python importa correctamente. Si no hay servidor Appium, los tests se omiten (`SkipTest`).

CI: job `nightly` (cron 04:00 UTC + `workflow_dispatch`).

---

## E2E Playwright (`tests/e2e/`)

### Arranque

Playwright levanta un servidor aislado (`tests/e2e/scripts/e2e_serve.py`):

- Datos bajo `tests/e2e/.runtime/` (no usa `%LOCALAPPDATA%\ELIA` del desarrollador)
- Stub de Puppeteer activo por defecto (`ELIA_E2E_STUB_PUPPETEER=1`)
- Si Chrome no está instalado, stub de preflight automático

**Antes de E2E:** reconstruir frontend si cambiaste `App.tsx` o `data-testid`:

```powershell
cd frontend
npm run build
```

### Proyectos Playwright

1. `license-flow` — activación de licencia (corre primero)
2. `app` — resto de specs (depende de `license-flow`)

### Specs principales

| Spec | Cobertura |
|------|-----------|
| `license.spec.ts` | Banner sin licencia, activación |
| `home.spec.ts` | Carga UI, pestañas |
| `job-demo.spec.ts` | Job demo + prompts |
| `record-popup.spec.ts` | **Popup «Grabar Interacciones»**, flujo puppeteer con stub |
| `validation.spec.ts` | URL requerida, doc-to-bdd |
| `platform-lock.spec.ts` | Módulo móvil bloqueado sin flag M |
| `settings.spec.ts` | Modal configuración, tema |

### Comandos útiles

```powershell
cd tests\e2e
npm run test:e2e          # headless
npm run test:e2e:headed   # con navegador visible
npm run test:e2e:ui       # UI de Playwright
npx playwright test specs/record-popup.spec.ts
```

Reporte HTML: `tests/e2e/report/` (gitignored).

---

## Stub de grabación web

Para E2E e integración sin abrir Chrome real:

- `tests/support/recorder_stub.py` — parchea `run_subprocess_with_automation_focus`, escribe el `.js` de salida y emite `BROWSER_READY`
- `tests/fixtures/stub_recorder.js` — equivalente ejecutable con `node` (smoke CI)

Desactivar stub E2E (grabación real):

```powershell
$env:ELIA_E2E_STUB_PUPPETEER = "0"
```

---

## CI (`.github/workflows/ci.yml`)

| Job | Contenido |
|-----|-----------|
| `python` | `run_all.py` + `run_integration.py` (smoke) |
| `e2e` | build frontend + Playwright (14 tests) |
| `integration-live` | manual / secrets — Jira + VE |
| `nightly` | cron + manual — Appium + Legacy |

---

## Variables de entorno (resumen)

| Variable | Efecto |
|----------|--------|
| `ELIA_SKIP_LICENSE` | **Debe estar vacía en tests** — `run_all.py` y fixtures la limpian |
| `ELIA_USER_DATA` | Aislada en API tests; E2E usa `tests/e2e/.runtime/UserData` |
| `ELIA_RUN_INTEGRATION=1` | Habilita tests Jira/VE con red real |
| `ELIA_RUN_NIGHTLY=1` | Habilita tests Appium/Legacy runtime |
| `ELIA_E2E_STUB_PUPPETEER=1` | Stub recorder en servidor E2E (default) |
| `ELIA_E2E_PORT` | Puerto del servidor E2E (default `8765`) |
| `ELIA_APPIUM_URL` | URL del servidor Appium (nightly) |

---

## Añadir tests

### Unit / API

1. Crear `tests/unit/test_mi_modulo.py` o `tests/api/test_mi_endpoint.py`
2. API: heredar de `ApiTestCase` y usar `elia_test_app()` de `tests/api/support.py`
3. Ejecutar: `python tests/run_all.py`

### Integración

1. Añadir `tests/integration/test_*.py`
2. Usar `@unittest.skipUnless(integration_enabled(), ...)` o `nightly_enabled()` de `tests/support/markers.py`
3. Ejecutar: `python tests/run_integration.py`

### E2E

1. Añadir Page Object en `tests/e2e/pages/` si hace falta
2. Spec en `tests/e2e/specs/` — usar `testLicensed` de `fixtures/elia-fixture.ts` si requiere licencia
3. Añadir `data-testid` en `frontend/src/App.tsx` y rebuild `frontend/dist`
4. Ejecutar: `npm run test:e2e`

---

## Gaps conocidos / roadmap

| Área | Estado | Próximo paso |
|------|--------|--------------|
| Puppeteer grabación real en CI | Smoke con stub | Job opcional con Chrome headless + `ELIA_E2E_STUB_PUPPETEER=0` |
| Popup «Grabar interacciones» | **Cubierto** (`record-popup.spec.ts`) | — |
| Jira/VE red real | Opt-in documentado | Secrets en GitHub + job `integration-live` |
| Appium dispositivo real | Status + import | Emulador Android en nightly |
| Legacy runtime | Notepad + flujo corto | App `.exe` dedicada en nightly |
| Rutas estáticas localhost | **Corregido** + test API | — |
| POST `/cancel` 404 | **Corregido** + test API | — |
