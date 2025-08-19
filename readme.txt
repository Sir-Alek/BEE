# Behave Extractor Engine (BEE) 🐝

Rápida y eficiente como una abeja, esta herramienta graba interacciones con páginas web y las convierte en pruebas automatizadas con Behave (BDD para Python).

## Características principales

- **Grabación intuitiva**: Graba tus interacciones con cualquier página web usando Puppeteer
- **Conversión inteligente**: Transforma los scripts grabados en:
  - Archivos `.feature` con sintaxis Gherkin
  - Steps de Behave listos para usar
  - Page Objects estructurados
  - Datos de prueba en JSON
- **Interfaz gráfica amigable**: Aplicación de escritorio fácil de usar
- **Soporte para elementos complejos**: Maneja clicks, formularios, dropdowns y más

## Cómo usar

1. **Grabar interacciones**:
   - Ingresa la URL del sitio a probar
   - Haz clic en "Grabar Interacciones"
   - Interactúa con la página en el navegador que se abre
   - Cierra el navegador para guardar la grabación

2. **Convertir a Behave**:
   - Haz clic en "Convertir a Behave"
   - Selecciona el archivo JS grabado
   - La herramienta generará automáticamente:
     - Archivo .feature en `behave/features/`
     - Steps en `behave/features/steps/`
     - Page Objects en `behave/pages/`
     - Datos de prueba en `behave/resources/data/`

## Estructura del proyecto

bee/
├── core/ # Código principal
│ ├── node/ # Node.js portable
│ ├── recorder.js # Script de grabación
│ └── puppeteer_script_converter.py # Conversor a Behave
├── grabaciones/ # Scripts grabados
├── behave/ # Salida generada
│ ├── features/ # Archivos .feature
│ ├── pages/ # Page Objects
│ └── resources/ # Datos de prueba
├── main.py # Interfaz gráfica
└── resources/ # Assets de la aplicación

## Requisitos

- Windows (compatible con Node.js portable incluido)
- Python 3.10 (para la interfaz y conversión)

## Notas importantes

- Las grabaciones se guardan en formato JavaScript (Puppeteer)
- La conversión genera código compatible con Selenium WebDriver
- Se recomienda revisar los selectores generados para asegurar su robustez
