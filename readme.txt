# Behave Extractor Engine (BEE)

Herramienta para grabar interacciones en páginas web y generar pruebas automatizadas en **Behave** (BDD con Gherkin) o pruebas **step-by-step** con evidencias.

## Cómo usar BEE

1. Inicia la aplicación (instalable o `python main.py` según tu entorno).
2. Abre la interfaz web local en el navegador (por defecto en `127.0.0.1`).
3. **Grabar:** indica la URL, inicia la grabación, interactúa en el navegador que se abre y cierra el navegador al terminar.
4. **Convertir a Behave o step-by-step:** elige el proyecto y el script grabado, selecciona las acciones y confirma. Los archivos generados se guardan en la carpeta de proyectos del usuario (por defecto bajo Documentos).

## Cómo usar

1. Grabar interacciones:
  ● Ingresa la URL del sitio a probar
  ● Haz clic en "Grabar Interacciones"
  ● Selecciona o crea un proyecto
  ● Asigna nombre al archivo de grabación
  ● Interactúa con la página en el navegador que se abre
  ● Cierra el navegador para guardar la grabación

2. Convertir a Behave:
  ● Haz clic en "Convertir a Behave"
  ● Selecciona el proyecto y el archivo JS grabado
  ● Elige las acciones a incluir en la conversión
  ● La herramienta generará automáticamente:
    - Archivo .feature en Documentos/BEE/behave/proyectos/[nombre]/features/ (o la ruta definida por BEE_USER_DATA)
    - Steps en .../features/steps/
    - Page Objects en .../pages/
    - Datos de prueba en .../resources/data/

3. Convertir a Step-by-Step:
  ● Haz clic en "Convertir a step by step"
  ● Selecciona el proyecto y el archivo JS grabado
  ● Elige las acciones a incluir en la conversión
  ● Decide si reorganizar el proyecto en la estructura step-by-step
  ● La herramienta generará:
    - Test case en Documentos/BEE/step_by_step/proyectos/[nombre]/tests/
    - JSON con información de pasos en .../resources/info_steps/
    - Evidencias en .../outputs/evidences/

## Estructura del proyecto

bee/
├── core/                 # Código principal
│   ├── __init__.py      # Sistema de desofuscación
│   ├── __dynamic_importer.py # Cargador de módulos ofuscados
│   ├── node_wrapper.py  # Wrapper para Node.js
│   ├── puppeteer_script_converter.py # Conversor a Behave
│   ├── step_by_step_converter.py # Conversor a step-by-step
│   ├── video_recorder.py # Grabador de pantalla
│   ├── node/            # Node.js portable incluido
│   └── recorder.js      # Script de grabación Puppeteer
├── behave/              # Plantilla vacía en el repo (la salida real va a Documentos/BEE/behave/…)
│   └── proyectos/       # Proyectos organizados por nombre
│       └── [nombre_proyecto]/
│           ├── scripts/       # Scripts grabados (.js)
│           ├── features/      # Archivos .feature
│           ├── features/steps/ # Steps de Behave
│           ├── pages/         # Page Objects
│           ├── resources/     # Datos de prueba
│           ├── outputs/       # Resultados y salidas
│           └── utils/         # Utilidades
├── step_by_step/        # Plantilla en el repo (salida real en Documentos/BEE/step_by_step/…)
│   └── proyectos/       # Proyectos organizados por nombre
│       └── [nombre_proyecto]/
│           ├── scripts/       # Scripts grabados (.js)
│           ├── tests/         # Tests step-by-step
│           ├── resources/     # Recursos e info_steps
│           ├── outputs/       # Evidencias y resultados
│           ├── grabaciones/   # Videos de las grabaciones
│           └── utils/         # Utilidades
├── grabaciones/         # Scripts grabados (ubicación legacy)
├── main.py             # Interfaz gráfica principal
└── resources/          # Assets de la aplicación
    ├── logo_bee_png_transparente.png
    ├── behave/         # Plantillas y recursos para Behave
    ├── models/gemma/   # Modelo Gemma 4 en GGUF (opcional; ver sección «Modelo de IA»)
    └── step_by_step/   # Plantillas y recursos para step-by-step

## Requisitos

● Python **3.10.11** (64-bit en Windows; recomendado para coincidir con el runtime empaquetado).
● Node.js **16+** (o el Node.js portable en `core/node/`; necesario para `npx` si ofuscas `recorder.js`).
● Chrome/Chromium instalado.
● **Tkinter:** incluido en el instalador oficial de Python para Windows (no viene de pip).

### Entorno virtual (recomendado para desarrollo y para PyInstaller)

Usa un **venv dedicado** solo para BEE, así PyInstaller solo incluirá lo instalado ahí (no librerías globales del sistema).

**Windows (PowerShell o cmd), desde la carpeta del proyecto:**

```text
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip setuptools wheel
pip install -r requirements.txt
```

**Activar en sesiones posteriores:** `.venv\Scripts\activate`

**Ejecutar la app:** `python main.py`

**Generar el .exe** (con el venv activado, frontend ya compilado si usas la UI web):

```text
python -m PyInstaller --noconfirm BEE.spec
```

o el pipeline completo: `python scripts/build_release.py` (ver sección «Protección / build de release»).

**Desactivar el venv:** `deactivate`

● Si en la misma máquina tienes **otras herramientas** (TensorFlow, PyTorch, JAX, etc.) instaladas en **otro** entorno, no pasa nada. Para el **build del exe** lo ideal es un **venv limpio** solo con `requirements.txt`: así PyInstaller no arrastra cientos de MB de dependencias que BEE no importa.

● Para el ejecutable en equipos finales: Windows 10/11 y Chrome; no hace falta Python instalado.

## Notas importantes

● **Datos de usuario:** los proyectos Behave y step-by-step se crean bajo **Documentos/BEE** (Windows: `%USERPROFILE%\\Documents\\BEE`). Para otra ubicación, define **`BEE_USER_DATA`** con la ruta raíz (por ejemplo `D:\\MisDatos\\BEE`). El «motor» instalado puede seguir en `Program Files`; los artefactos generados quedan fuera.
● **Memoria local de IA:** correcciones aceptadas (script + feature editado) se guardan en `bee_memory.json` dentro de esa misma carpeta de datos, para enriquecer prompts futuros de Gemma (sin reentrenar el GGUF).

● El producto se distribuye como ejecutable .exe que incluye Python 3.10.0 empaquetado
● Las grabaciones se guardan en formato JavaScript (Puppeteer)
● Ambas conversiones generan código compatible con Selenium WebDriver
● El sistema de step-by-step incluye generación de reportes PDF con evidencias
● Se recomienda revisar los selectores generados para asegurar su robustez
● Para problemas de grabación, ejecutar install_puppeteer.bat para reinstalar Puppeteer

## Modelo de IA (Gemma 4, GGUF)

● Ruta esperada en el árbol del proyecto: `resources/models/gemma/gemma-4-E4B-it-Q4_K_M.gguf`
● Los archivos `*.gguf` bajo `resources/models/` están en `.gitignore` y no se suben al repositorio.
● Para desarrollo o para generar el `.exe` con el modelo incluido, copia manualmente el GGUF a esa ruta **antes** de ejecutar PyInstaller (`BEE.spec` ya empaqueta la carpeta `resources/` completa; si el archivo existe en el momento del build, quedará en la distribución).
● Si el archivo no está presente, las funciones que dependan del modelo deberán operar en modo heurístico o mostrar un aviso claro (según la implementación de «Activar IA»).
● Resolución de ruta en código: `core/gemma_model_paths.py` (`resolve_gguf_path`, `is_gguf_available`, `get_gemma_model_info`).
● Inferencia local: `core/gemma_inference.py` con **`llama-cpp-python`** (sin binario `llama-cli` aparte). Opcional: `BEE_LLAMA_N_CTX` (default 4096), `BEE_LLAMA_N_GPU_LAYERS` (default 0 = CPU).
● La grabación puede generar `*_bee_meta.json` junto al `.js` (metadatos DOM para IA). La UI web incluye «Activar IA» en la conversión a Behave; sin modelo o sin `llama-cpp-python` se usa el modo heurístico.

## Interfaz web (FastAPI + React)

● Tras actualizar el código, compila el frontend: `cd frontend && npm install && npm run build` (genera `frontend/dist` que sirve la API local).
● Permite ventanas emergentes para `127.0.0.1`: el inicio debe quedar en una pestaña y el flujo (grabación/conversión) en otra; si el navegador bloquea pop-ups, el flujo puede abrirse en la misma pestaña y reemplazar el inicio.
● La aplicación no debe cerrar el navegador sola al terminar; usa la pestaña de inicio para nuevas tareas.
● El aviso azul en inicio desaparece cuando termina el flujo en la otra pestaña (BroadcastChannel) o a los 5 minutos.
● En la pestaña de resultado, «Volver al inicio» enfoca la pestaña de inicio y cierra la de trabajo (evita duplicar inicio).
● **Modo oscuro:** botón «Oscuro / Claro» en la cabecera; la preferencia se guarda en el navegador (`localStorage`) y se sincroniza entre pestañas abiertas (`BroadcastChannel`). Las pestañas de trabajo reciben `?theme=dark|light` al abrirse desde inicio para aplicar el mismo tema.

## Protección / build de release (Cython + JS)

● Pipeline unificado: `scripts/build_release.py` (Cython opcional + ofuscador JS + PyInstaller).
● **Cython (opcional):** `python setup_cython.py build_ext --inplace` genera `core/*.pyd` para los módulos listados en `core/_cython_build_manifest.py`.
● **JavaScript:** `javascript-obfuscator` vía `npx`; perfil seguro en `scripts/build_release.py` (no `string-array` / control-flow en código que Puppeteer inyecta en el navegador).
● **PyInstaller (`BEE.spec`):** en el ejecutable solo se incluye **`core/recorder.obfuscated.js`** si existe en el momento del build (generado por `scripts/build_release.py` / ofuscador). Si no existe, se empaqueta **`recorder.js`** plano para que el grabador no quede sin motor. En entregas, ejecuta el pipeline de release **antes** de PyInstaller para incluir la versión ofuscada.
● **PyInstaller (resto):** `python scripts/build_release.py` (o con `--cython`). Si hay `.pyd`, el script puede **retirar** los `.py` duplicados de `dist/BEE/core/`.

## Licencia offline (demo 15 días, activación por clave, kill switch)

● **Demo:** 15 días desde el primer arranque (estado en `%LOCALAPPDATA%\BEE\license_state.json` en Windows). Sin activación, los trabajos (grabar / convertir) se bloquean; la UI web permite introducir la **clave de activación**.
● **Clave:** derivada por máquina (huella mostrada en la UI). Generar con `python scripts/generate_license_key.py --machine <huella>` (mismo secreto que `core/bee_license.py`; **cambiar `_LICENSE_SEED`** en builds de cliente).
● **Activación silenciosa:** variable de entorno `BEE_ACTIVATION_KEY=<clave>` antes de arrancar.
● **Desarrollo:** `BEE_SKIP_LICENSE=1` omite la comprobación (no usar en entregas).
● **Kill switch** (sin red): si existe cualquiera de estos archivos, la app no arranca: `%LOCALAPPDATA%\BEE\KILL`, `%LOCALAPPDATA%\BEE\bee_revoked.flag`, o junto al `.exe`: `bee.kill`, `BEE_KILL`.

## Troubleshooting

● Si encuentras errores de "MODULE_NOT_FOUND" con Puppeteer:
  - Ejecuta el archivo install_puppeteer.bat incluido
  - Asegúrate de tener Chrome instalado en tu sistema
  - Verifica que no haya bloqueos de firewall que impidan la descarga de dependencias

● Para problemas de ejecución del .exe:
  - Ejecuta como administrador
  - Verifica que tengas .NET Framework actualizado
  - Asegúrate de tener los Visual C++ Redistributables instalados
