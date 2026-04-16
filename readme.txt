# Behave Extractor Engine (BEE)

Herramienta para grabar interacciones en páginas web y generar pruebas automatizadas en **Behave** (BDD con Gherkin) o pruebas **step-by-step** con evidencias.

## Cómo usar BEE

1. Inicia la aplicación (instalable o `python main.py` según tu entorno).
2. Abre la interfaz web local en el navegador (por defecto en `127.0.0.1`).
3. **Grabar:** indica la URL, inicia la grabación, interactúa en el navegador que se abre y cierra el navegador al terminar.
4. **Convertir a Behave o step-by-step:** elige el proyecto y el script grabado, selecciona las acciones y confirma. Los archivos generados se guardan en la carpeta de proyectos del usuario (por defecto bajo Documentos).

Para instalación desde código, Node portable, entorno virtual, licencia y empaquetado, consulta **`readme_dev.md`**.
