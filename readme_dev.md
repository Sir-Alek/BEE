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

## Ramas Git

Convención útil: `main`, `change_tests` y una rama de trabajo `cursor/...`. Elimina ramas fusionadas que ya no necesites en el remoto para mantener el repositorio claro.
