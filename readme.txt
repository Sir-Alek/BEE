# Behave Extractor Engine (BEE) 🐝

Rápida y eficiente como una abeja, esta herramienta graba interacciones con páginas web y las convierte en pruebas automatizadas con Behave (BDD para Python) o pruebas step-by-step tradicionales.

## Características principales

● Grabación intuitiva: Graba tus interacciones con cualquier página web usando Puppeteer
● Doble sistema de conversión: Transforma los scripts grabados en:
  - Behave BDD: Archivos .feature con sintaxis Gherkin + Steps + Page Objects
  - Step-by-Step: Pruebas unittest tradicionales con captura de evidencias
● Grabación de video opcional: Captura video de las interacciones durante la grabación
● Interfaz gráfica amigable: Aplicación de escritorio fácil de usar
● Soporte para elementos complejos: Maneja clicks, formularios, dropdowns, esperas y más
● Selección de acciones: Permite elegir qué acciones convertir de la grabación
● Gestión de proyectos: Organiza tus pruebas por proyectos independientes

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