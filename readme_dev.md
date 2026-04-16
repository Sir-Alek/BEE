# BEE — Guía para desarrolladores

## Entorno virtual (Python)

Desde la raíz del repositorio:

```text
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
```

Activar en sesiones posteriores: `.venv\Scripts\activate` (Windows) o `source .venv/bin/activate` (Linux/macOS).

Ejecutar la app: `python main.py`

## Node.js en `core/node` (grabación Puppeteer)

El repositorio **no incluye** el binario de Node ni `node_modules` (demasiado pesado). Debes generarlos en tu máquina:

1. Instala [Node.js LTS](https://nodejs.org/) (16+), o copia una distribución **portable** de Node en `core/node/` de forma que existan `core/node/node.exe` (Windows) y la carpeta `core/node/node_modules/`.
2. Con Node en el PATH, desde `core/node/`:

```text
cd core/node
npm install
```

Esto instala las dependencias definidas en `package.json` (p. ej. Puppeteer). El código usa esta ruta en tiempo de ejecución y, en el `.exe`, PyInstaller empaqueta `core/node` **tal como esté en tu máquina al construir** el instalable.

## Frontend (React / Vite)

```text
cd frontend
npm install
npm run build
```

La salida va a `frontend/dist/`, que sirve la UI web local.

## Licencia (si tu rama incluye `core/bee_license.py`)

- **Demo:** periodo limitado desde el primer arranque; estado en carpeta de datos de usuario (p. ej. `%LOCALAPPDATA%\BEE\` en Windows).
- **Activación:** introduce la clave en la pantalla de inicio de la UI web, o define `BEE_ACTIVATION_KEY` antes de arrancar.
- **Desarrollo:** `BEE_SKIP_LICENSE=1` omite comprobaciones (solo entorno de desarrollo).
- **Kill switch local:** archivos indicados en el código de licencia (p. ej. `bee.kill` junto al exe) desactivan el arranque.

Los detalles exactos dependen de la versión del módulo de licencia en tu rama.

## Ramas Git recomendadas

Mantener solo tres líneas de trabajo en remoto facilita el mantenimiento:

- `main` — estable.
- `change_tests` — integración de pruebas / plantillas Behave.
- `cursor/<nombre>` — trabajo activo del agente (una rama a la vez o consolidar en una).

Para limpiar ramas antiguas en GitHub: eliminar las ramas que ya no usas desde la interfaz o con `git push origin --delete <rama>`.
