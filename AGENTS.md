# AGENTS.md

## Cursor Cloud specific instructions

### Overview

ELIA (Evolving Learning & Intelligent Automation) is a local-first QA engineering suite. It records web interactions via Puppeteer, then generates BDD test code (Behave/Gherkin) or step-by-step test documentation with evidence. The app runs as a single Python process (`python main.py`) that serves a React SPA via FastAPI/Uvicorn on localhost.

### Required Python version

The project requires **Python 3.10** (installed via deadsnakes PPA at `python3.10`). The pinned dependencies in `requirements.txt` are incompatible with Python 3.12 (e.g. `numpy==1.24.3`). Note: the `numpy` pin conflicts with `opencv-python==4.12.0.88` (which needs `numpy>=2`); the update script installs most deps first then installs opencv/matplotlib separately, letting pip resolve numpy to a compatible version.

### Running the application

```bash
source /workspace/.venv/bin/activate
ELIA_SKIP_LICENSE=1 python main.py
```

- `ELIA_SKIP_LICENSE=1` bypasses offline license checks (required for dev/CI).
- The app binds to `127.0.0.1` on a dynamic port. Check terminal output or `netstat -tlnp | grep python` for the port.
- The frontend SPA must be pre-built (`frontend/dist/`). If missing, the root route returns an HTML error page.

### Key commands (see `readme_dev.md` for full details)

| Task | Command |
|---|---|
| Install Python deps | `source .venv/bin/activate && pip install -r requirements.txt` (see note about numpy conflict) |
| Install Puppeteer recorder deps | `cd core/node && npm install` |
| Install + build frontend | `cd frontend && npm install && npm run build` |
| Run frontend dev server | `cd frontend && npm run dev` |
| Run app (web mode, default) | `ELIA_SKIP_LICENSE=1 python main.py` |

### Gotchas

- **TypeScript en CI**: `npm run typecheck` (vía `npm run build`) debe pasar sin errores. Vite no typecheckea por sí solo; el script `build` ejecuta `tsc --noEmit` primero.
- **`llama-cpp-python`** is listed in `requirements.txt` but is optional (local AI inference). It requires C++ compilation and a GGUF model file. The app gracefully degrades without it (`AI status` shows unavailable).
- **No database or external services required**: all state is file-based. Jira and Value Edge integrations are optional and require external credentials.
- **Puppeteer recording** requires Chrome/Chromium and a display server. In headless cloud environments, recording may not work but conversion and the web UI function normally.
