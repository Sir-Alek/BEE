Guía rápida — Automatización legacy (Windows)

Los proyectos Behave legacy se generan al convertir una grabación de escritorio. ELIA engancha la UI Automation a una ventana concreta de Windows.

1. Prepara la aplicación
   - Abre la app de escritorio que quieres automatizar, o indica la ruta al .exe para que ELIA la lance.
   - Copia el título exacto de la ventana (como aparece en la barra de tareas).

2. Configura la grabación
   - Campo «Ventana de la aplicación»: título exacto, sensible a mayúsculas y espacios.
   - «Ejecutable (opcional)»: solo si ELIA debe abrir la app por ti.

3. Graba el flujo
   - Pulsa Grabar e interactúa con la aplicación.
   - Detén la grabación cuando termines el recorrido.

4. Convierte a Behave
   - Convierte con legacy_to_behave y elige nombre de proyecto (behave/legacy/).
   - Revisa feature, steps y page objects generados.

5. Ejecuta
   - Selecciona el proyecto en «Ejecutar Behave» y lanza el .feature.
   - La app debe estar accesible con el mismo título de ventana que usaste al grabar.

Notas
   - Solo Windows: legacy usa pywinauto / UI Automation del sistema.
   - Si la ventana cambia de título (diálogos, idioma), actualiza la configuración o regraba.
   - Evidencias PDF: activa GENERATE_EVIDENCE al ejecutar si necesitas informe.
