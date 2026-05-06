# ELIA (Evolving Learning & Intelligent Automation)

ELIA graba tus interacciones en páginas web y genera pruebas en **Behave** (BDD) o en formato **step-by-step** con evidencias.
ELIA es una suite de ingeniería de calidad local-first. Combina la grabación de interacciones web con un modelo de IA generativa,
que se ejecuta directamente en la computadora del tester.
A diferencia de las herramientas tradicionales, ELIA lee Historias de Usuario en Word o Excel, graba el flujo, y genera código BDD (Behave)
que se adapta y aprende del estilo de redacción de tu equipo, todo bajo una arquitectura compilada y segura para entornos bancarios.

## Cómo usar el programa

1. **Inicia ELIA** (acceso directo al instalable o como indique tu entorno).
2. Se abre el **navegador** en la dirección local de la aplicación (por ejemplo `http://127.0.0.1` y un puerto). Esa es la **pantalla de inicio**: conviene dejarla abierta.
3. **Modo de pantalla:** en la barra superior o junto al título «ELIA Web UI» puedes elegir **Modo oscuro** o **Modo claro**. La preferencia se guarda en el navegador y se aplica también en las pestañas de grabación y conversión.
4. **Grabar interacciones:** escribe la URL del sitio, pulsa «Grabar Interacciones» y sigue los pasos en la **nueva pestaña**. Interactúa en el navegador que se abre; al **cerrar ese navegador** se guarda la grabación.
5. **Convertir a Behave o a step-by-step:** pulsa el botón correspondiente, elige proyecto y archivo grabado cuando se te pida, selecciona las acciones y confirma. Los archivos generados se guardan en la carpeta de proyectos del usuario (por defecto bajo **Documentos**, carpeta **ELIA**).
6. Si aparece **licencia en modo demostración**, introduce la clave en la misma pantalla de inicio cuando tu organización te la facilite, o consulta con soporte.

ELIA amplía el core con integraciones avanzadas (p. ej. Jira, Value Edge, Gherkin en lote). Detalles de configuración: **`readme_dev.md`** junto al resto de la documentación técnica.
