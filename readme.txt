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
    - Archivo .feature en behave/proyectos/[nombre]/features/
    - Steps en behave/proyectos/[nombre]/features/steps/
    - Page Objects en behave/proyectos/[nombre]/pages/
    - Datos de prueba en behave/proyectos/[nombre]/resources/data/

3. Convertir a Step-by-Step:
  ● Haz clic en "Convertir a step by step"
  ● Selecciona el proyecto y el archivo JS grabado
  ● Elige las acciones a incluir en la conversión
  ● Decide si reorganizar el proyecto en la estructura step-by-step
  ● La herramienta generará:
    - Test case en step_by_step/proyectos/[nombre]/tests/
    - JSON con información de pasos en step_by_step/proyectos/[nombre]/resources/info_steps/
    - Evidencias en step_by_step/proyectos/[nombre]/outputs/evidences/

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
├── behave/              # Salida generada para Behave
│   └── proyectos/       # Proyectos organizados por nombre
│       └── [nombre_proyecto]/
│           ├── scripts/       # Scripts grabados (.js)
│           ├── features/      # Archivos .feature
│           ├── features/steps/ # Steps de Behave
│           ├── pages/         # Page Objects
│           ├── resources/     # Datos de prueba
│           ├── outputs/       # Resultados y salidas
│           └── utils/         # Utilidades
├── step_by_step/        # Salida generada para step-by-step
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

● Para uso directo con Python:
  - Python 3.10.0
  - Node.js 16+ (o usar el Node.js portable incluido)
  - Chrome/Chromium instalado

● Para el ejecutable:
  - Windows 10/11
  - Chrome/Chromium instalado

## Notas importantes

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

## Interfaz web (FastAPI + React)

● Tras actualizar el código, compila el frontend: `cd frontend && npm install && npm run build` (genera `frontend/dist` que sirve la API local).
● Permite ventanas emergentes para `127.0.0.1`: el inicio debe quedar en una pestaña y el flujo (grabación/conversión) en otra; si el navegador bloquea pop-ups, el flujo puede abrirse en la misma pestaña y reemplazar el inicio.
● La aplicación no debe cerrar el navegador sola al terminar; usa la pestaña de inicio para nuevas tareas.
● El aviso azul en inicio desaparece cuando termina el flujo en la otra pestaña (BroadcastChannel) o a los 5 minutos.
● En la pestaña de resultado, «Volver al inicio» enfoca la pestaña de inicio y cierra la de trabajo (evita duplicar inicio).

## Troubleshooting

● Si encuentras errores de "MODULE_NOT_FOUND" con Puppeteer:
  - Ejecuta el archivo install_puppeteer.bat incluido
  - Asegúrate de tener Chrome instalado en tu sistema
  - Verifica que no haya bloqueos de firewall que impidan la descarga de dependencias

● Para problemas de ejecución del .exe:
  - Ejecuta como administrador
  - Verifica que tengas .NET Framework actualizado
  - Asegúrate de tener los Visual C++ Redistributables instalados
