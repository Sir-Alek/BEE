# Changelog

Todos los cambios notables de ELIA se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones usan [Semantic Versioning](https://semver.org/lang/es/).

## [0.9.50] - 2026-05-19

### Añadido

- **Inteligencia de Requerimientos — publicación multi-destino (Estrategia 2):** tras revisar el Gherkin en el job, panel opcional de publicación antes de continuar.
- Adaptadores backend: Git (GitHub/GitLab/Azure Repos), Jira vanilla (ADF), Jira Xray, ValueEdge `bdd_specs`, Azure DevOps Work Item, archivo `.feature` local.
- API `POST /api/req/publish`, `POST /api/req/publish/test`, `GET /api/req/publish/targets`.
- Perfiles de conectores **v2**: campos Git, Azure DevOps, modo Jira vanilla/Xray, IDs por defecto para publicación.
- Configuración ampliada en **Conectores** (Git, Azure, campos Jira/VE de publicación).

### Cambiado

- Separación explícita **generación** (Gherkin) vs **publicación** (Multi-Target Adapter).
- Migración automática de perfiles conectores v1 → v2 al cargar/guardar.

## [0.9.43] - 2026-05-28

### Añadido

- Runner web Behave: checkbox **«Mostrar navegador»** para ejecutar con Chrome visible (`HEADLESS=false`); headless sigue siendo el valor por defecto.

### Cambiado

- Texto de ayuda bajo el campo `features` en «Ejecutar y editar proyecto», aclarando filtro de ejecución vs. editor de archivos.

## [0.9.42] - 2026-05-28

### Añadido

- **Fase 6 — Reportes enriquecidos opt-in:** PDF/HTML post-carga con percentiles p50/p95/p99, endpoints CSV y métricas agregadas; historial ligero en `outputs/reports/load_history.json`; comparativa entre ejecuciones en UI; evidencia PDF/JSON de suite funcional bajo demanda.
- **Fase 7 — Integración ELIA nativa:** deduplicación al importar capturas web (method+URL); sincronización de `base_url` desde grabación web al entorno API; límites de carga documentados en `/api/modules/status` (`api_limits`).

### Cambiado

- Importación de tráfico devuelve contadores `imported` / `skipped`.
- Exportación de carga admite `format: pdf | html` y `enriched: true` (por defecto).

## [0.9.41] - 2026-05-28

### Cambiado

- Pestaña **Pruebas API** reorganizada con dos subpestañas estilo Automatización UI (Web/Móvil/Legacy): **Postman** (constructor, entornos, importación, capturas) y **JMeter-lite / Locust** (CSV, suite funcional, carga y métricas).
- Barra de proyecto y entorno compartida entre ambas subpestañas; al cargar un escenario se abre automáticamente la vista Postman.
- Peso Locust y selección masiva de escenarios movidos exclusivamente a la subpestaña de carga.

## [0.9.40] - 2026-05-28

### Añadido

- **Fase 1 — Suite runner:** `POST /api/api/run-suite` ejecuta escenarios en orden con resumen pass/fail en RAM; UI «Ejecutar suite» con opción continuar si falla.
- **Fase 2 — Correlación dinámica:** extractores JSONPath, regex y header; variables de sesión compartidas entre pasos de la suite.
- **Fase 3 — Data-driven:** CSV en `resources/data/`; suites iteran filas parametrizadas (`{{columna}}`).
- **Fase 4 — Aserciones avanzadas:** JSONPath real, duración máxima (`max_duration_ms`), regex y body_contains en motor y UI.
- **Fase 5 — Dashboard de carga:** métricas Locust en vivo (`GET /api/api/load-test/{run_id}/metrics`), CSV headless opt-in, pesos por escenario y parámetros spawn/duración en UI.
- Flujos persistidos en `flows/*.json` y endpoints de gestión de CSV/flujos.

### Cambiado

- Locust genera tareas con `@task(peso)` según peso del escenario.
- `build_locust_command` admite `--csv` para métricas sin PDF automático.

## [0.9.32] - 2026-05-28

### Añadido

- Evidencias API opt-in para peticiones individuales: botones «Exportar evidencia (PDF)» y «Exportar evidencia (JSON)» tras ejecutar una petición; nunca se escriben archivos al pulsar Enviar.
- Evidencias opt-in para carga Locust: checkbox «Permitir reporte PDF al finalizar» (desmarcado por defecto) y botón «Generar reporte de carga (PDF)» visible solo al terminar la ejecución.
- Endpoints `POST /api/api/export/request-evidence` y `POST /api/api/export/load-evidence` para generar PDF/JSON bajo demanda.
- Módulo `core/api_automation/api_evidence_report.py` con plantillas PDF ligeras para petición HTTP y resumen Locust.
- Panel de respuesta ampliado: headers de respuesta desplegables además de status, tiempo, aserciones y body.

### Cambiado

- Cada fila de header (globales y de petición) incluye botón ✕ para eliminarla; al borrar la última queda una fila vacía editable.
- Las pruebas de carga mantienen métricas en memoria/consola (`GENERATE_EVIDENCE=false`); el disco solo se usa si el usuario exporta evidencia explícitamente.

### Corregido

- Corrección de recursión infinita entre `ensure_api_project` y `ensure_project_defaults` al crear proyectos API nuevos.

## [0.9.31] - 2026-05-28

### Añadido

- Módulo API rediseñado estilo Postman/JMeter-lite: ejecución HTTP directa con `POST /api/api/execute`, sin depender de Behave para probar endpoints.
- Gestor de entornos por proyecto (`environments/*.json`) con interpolación de variables `{{nombre}}` en URL, headers y body.
- Headers globales de proyecto (`project.json`) con fusión automática (los headers de la petición tienen prioridad).
- Importación de colecciones Postman v2.1 y especificaciones OpenAPI 3 como escenarios JSON reutilizables.
- Selección de escenarios para pruebas de carga Locust desde la pestaña API.

### Cambiado

- Proyectos API nuevos ya no generan scaffold Behave (`features/`, `behave.ini`); el flujo principal es constructor manual, capturas e importación.
- La pestaña API sustituye los botones «Generar .feature Behave» por Enviar, entornos y panel de respuesta integrado.
- El endpoint `/api/api/convert` queda marcado como obsoleto; se mantiene solo por compatibilidad con proyectos legacy.

## [0.9.21] - 2026-05-27

### Corregido

- Navegación limpia entre plataformas: Al cambiar entre pruebas Web, Móvil o de Escritorio, la interfaz ahora limpia por completo el proyecto anterior, reinicia los selectores de pantalla y actualiza el árbol de archivos de forma automática para evitar mezclar datos de diferentes entornos.
- Optimización en la selección de proyectos: Se eliminaron las alertas de error inesperadas que aparecían si seleccionabas un proyecto en el entorno Web que no existía en las pestañas Móvil o Legacy. Ahora el sistema selecciona automáticamente el primer proyecto válido disponible o muestra la lista vacía de forma transparente.

## [0.9.20] - 2026-05-27

### Añadido

- Asistente de autocompletado inteligente: El editor de pruebas integrado ahora incluye sugerencias contextuales automáticas (accesibles al escribir o mediante el atajo Ctrl + Espacio). El asistente reconoce el tipo de archivo abierto para sugerirte palabras clave de Gherkin, pasos ya definidos en el proyecto, funciones de automatización de la plataforma y estructuras de datos en tiempo real, reflejando incluso los cambios del borrador actual antes de guardarlo.

### Cambiado

- Panel de archivos simplificado: El árbol de exploración del editor de código ahora solo muestra los archivos esenciales para tus flujos de automatización (escenarios, pasos de prueba, páginas de objetos y datos de soporte), manteniendo ocultos los archivos internos del sistema para una navegación más limpia. 
- Selector de proyectos mejorado: Se reemplazó el cuadro de texto tradicional por un menú desplegable nativo mucho más intuitivo y estable para cambiar de proyecto rápidamente en cualquiera de las plataformas.

## [0.9.10] - 2026-05-27

### Añadido

- Editor de código avanzado integrado: Se incorporó un espacio de edición de pruebas con herramientas de tipo profesional que incluye resaltado de colores para scripts de automatización y escenarios Gherkin, numeración de líneas, soporte para temas claro/oscuro, modo pantalla completa y un área de trabajo ampliada para modificar tus pruebas cómodamente sin salir de la aplicación. Incluye soporte para el guardado rápido tradicional mediante Ctrl + S.
- Visor nativo de reportes de evidencias: Tras ejecutar una prueba, ahora podrás previsualizar tus reportes PDF embebidos directamente dentro de la interfaz, descargarlos de forma individual, alternar entre múltiples documentos o abrir la carpeta contenedora con un solo clic gracias a la detección automática de resultados del sistema..

### Cambiado

- Consola de ejecución ajustable: Diseñamos una consola interactiva más flexible; ahora puedes arrastrar libremente el borde superior del panel de ejecución para ajustar su tamaño según tus necesidades de visualización en tiempo real.
- Generación automática de reportes: Las evidencias y reportes estructurados en PDF ahora se mantienen siempre activos y se generan de forma obligatoria tras cada ejecución desde el panel unificado, asegurando que tus resultados queden respaldados sin configuraciones adicionales.

### Corregido

- Acceso inmediato a documentos de evidencias: Se solucionó un inconveniente que dificultaba encontrar los reportes generados en el equipo; ahora todos los documentos e imágenes de evidencia quedan visibles y accesibles directamente desde la pantalla de resultados de la interfaz, sin necesidad de rastrear rutas de carpetas internas.

## [0.9.0] - 2026-05-27

### Añadido

- Espacio de trabajo unificado para edición y ejecución: Nuevo panel centralizado «Ejecutar y editar proyecto» disponible en todas las pestañas de automatización (Web, Móvil, Escritorio y API). Desde este espacio puedes explorar tus escenarios organizados, modificar el código de tus scripts con herramientas de guardado rápido y lanzar ejecuciones en vivo con monitoreo de rendimiento interactivo.
- Asistente de IA para automatización de servicios: Incorporamos la inteligencia de Gemma local para ayudarte a generar validaciones automáticas de datos de forma desconectada. Al transformar tus flujos de datos capturados en escenarios BDD, la IA te sugerirá de manera predictiva los criterios de verificación esperados para tus respuestas de integración.
- Captura inteligente de tráfico en segundo plano: Durante tus grabaciones en dispositivos móviles o aplicaciones de escritorio híbridas, ahora puedes activar de forma opcional el registro del tráfico de datos oculto de la aplicación. El sistema estructurará y guardará de forma transparente estos flujos para utilizarlos como base en tus validaciones de servicios.

### Cambiado

- Gestión de entornos por plataforma: El motor de conversión ahora configura los archivos de soporte y las plantillas de entorno de forma inteligente según la plataforma seleccionada (Web, Móvil, Escritorio o API), aplicando automáticamente los marcadores visuales y logos del producto correspondientes.
- Flujo de automatización sin interrupciones: Añadimos una sección interactiva en la parte inferior de las pestañas principales que te permite seleccionar tus proyectos, editar el código fuente y ejecutar las pruebas en vivo sin necesidad de abandonar tu flujo de trabajo principal o cambiar de pestaña.

## [0.8.10] - 2026-05-26

### Añadido

- Opciones de captura web personalizadas: Antes de iniciar una grabación en el navegador, ahora dispones de una pantalla de configuración previa con casillas independientes que te permiten elegir si deseas capturar video de la pantalla, registrar el tráfico de datos en segundo plano, o ambas opciones antes de la confirmación final.
- Mayor control en los asistentes guiados: Se incluyeron botones de Regresar y Cancelar en las ventanas de confirmación de tareas. Al cancelar, el sistema detendrá el proceso de inmediato de forma segura, notificará al backend y cerrará automáticamente la pestaña del flujo para mantener limpio tu espacio de trabajo. 

### Cambiado

- Instalador Windows (`ELIA_Setup.iss`) sincronizado a **0.8.10**.
- Interfaz principal interactiva mejorada: El aviso visual en pantalla que indica que el flujo de trabajo se abrió en otra pestaña ahora desaparece de forma inteligente y automática en el momento en que decides cerrar, cancelar o finalizar la grabación activa.

### Corregido

- Corrección en el inicio de grabaciones web: Se solucionó un inconveniente que mostraba la alerta "URL requerida" de forma errónea a pesar de tener la dirección web escrita correctamente en el formulario de inicio.
- Validación de acciones seleccionadas: El asistente ahora muestra una advertencia clara y detiene de forma segura el proceso si intentas generar un proyecto de automatización sin haber marcado ninguna acción registrada previamente en la lista de verificación.

## [0.8.0] - 2026-05-26

### Añadido

- Nuevo módulo especializado en Pruebas de API y Rendimiento: Se incorporó la pestaña dedicada a la verificación e integración de flujos de servicios. Ahora puedes capturar solicitudes de datos directamente desde tus grabaciones en el navegador, estructurar escenarios de verificación rápidos, convertirlos a scripts de automatización con consolas de monitoreo en tiempo real y generar pruebas de carga a gran escala de manera unificada bajo la misma licencia vigente.

## [0.7.20] - 2026-05-22

### Añadido

- Sistema de diagnóstico local y seguro: Se implementó un generador de reportes de errores que funciona de forma 100% local (offline-first). Si una tarea llega a interrumpirse, la aplicación crea un registro de diagnóstico aislado que puedes descargar al instante como un archivo de texto plano (.txt)
- Asistente de soporte en fallos: Nueva opción visual «Descargar reporte de error» dentro de las pantallas de tareas fallidas. Esta función incluye un aviso de privacidad transparente y un enlace directo para enviar tus comentarios al formulario de la comunidad Beta.
- Privacidad de datos reforzada: El sistema ahora limpia, oculta y remueve de forma automática cualquier información sensible (como tokens de acceso, contraseñas de conectores o nombres de rutas de carpetas personales) antes de exportar un reporte o procesar estados internos, garantizando que tus credenciales corporativas jamás queden expuestas.

### Cambiado

- Sección "Acerca de" informativa: Se actualizó este panel para mostrar con total claridad la ruta exacta donde se almacenan tus registros de ejecución locales en el equipo, facilitando el acceso rápido al formulario de retroalimentación de la fase Beta.
- Log de ejecución acotado: El archivo `elia_execution.log` usa rotación automática (~20 MB máximo) y registra solo eventos de ELIA, sin ruido del servidor web. Los reportes antiguos en `error_reports/` se podan automáticamente.

### Corregido

- Plantilla de reporte de error en español (incluido aviso de privacidad) y regeneración al descargar desde la interfaz.

## [0.7.10] - 2026-05-22

### Cambiado

- Independencia de módulos centrales: Se separó por completo la lógica interna que gestiona las licencias, los conectores externos y las grabaciones móviles. Al aislar estos servicios, se previene que una interrupción en un módulo específico afecte al rendimiento general del software, haciendo que ELIA sea mucho más ligera y tolerante a fallos.
- Optimización de fluidez en menús y paneles: Rediseñamos la forma en que las pantallas comparten configuraciones y preferencias en segundo plano. Este cambio estructural elimina procesos internos redundantes, lo que se traduce en una navegación entre menús globales notablemente más rápida y con menor consumo de memoria.
- Interacciones en el espacio de trabajo más ágiles: Los elementos del espacio de trabajo (ventanas de confirmación, cuadros de selección y paneles de vista previa BDD) ahora operan de manera modular. Lo que implica transiciones mucho más suaves y una respuesta inmediata de la interfaz al interactuar con los flujos de automatización generados.

## [0.7.0] - 2026-05-22

### Añadido

- Nueva arquitectura interna de la interfaz: Se reestructuró por completo el diseño interno de la aplicación, separando las secciones principales (Inicio, Panel de Trabajo, Configuración y Estilos) en módulos independientes. Esto permite una carga inicial de la aplicación mucho más rápida y una navegación más fluida.

### Cambiado

- Núcleo del sistema optimizado: Se simplificó drásticamente el componente central que gestiona la interfaz visual, reduciendo su complejidad interna en más de un 75%. Esta mejora previene congelamientos visuales y garantiza una excelente estabilidad a largo plazo.
- Modularización de espacios de trabajo: Las pantallas de configuración, el inicio de tareas y el área de trabajo ahora operan de forma independiente por debajo de la interfaz. Este cambio estructural se realizó manteniendo intactos todos tus flujos de trabajo actuales, garantizando la total compatibilidad con tus configuraciones y automatizaciones existentes.

## [0.6.70] - 2026-05-22

### Añadido

- Formularios optimizados por plataforma: Las configuraciones de grabación (Web, Móvil y Escritorio Legacy) ahora cuentan con campos personalizados e inteligentes que validan los datos automáticamente antes de iniciar cualquier conversión.
- Línea de tiempo en tiempo real: Nueva sección visual interactiva que muestra el progreso paso a paso de lo que está sucediendo durante las grabaciones móviles y de aplicaciones de escritorio.
- Interfaz más fluida y eficiente: Se optimizó drásticamente el sistema de comunicación interna de la aplicación. Las actualizaciones de estado ahora son prácticamente instantáneas durante la grabación y consumen menos recursos de tu equipo cuando estás en espera.
- Mayor estabilidad general: Implementamos controles de calidad estrictos en el proceso de empaquetado de la aplicación para prevenir fallos visuales e interrupciones inesperadas en la interfaz.

### Cambiado

- Mensajes de estado más claros: Los eventos mostrados durante las capturas de aplicaciones móviles y de escritorio ahora son mucho más descriptivos (indicando con precisión cuándo se detecta la ventana, cuándo se vincula el dispositivo o cuándo se toman evidencias).
- Asistente de conversión inteligente: El motor de captura ahora es más estricto al verificar los requisitos de cada tipo de entorno, asegurando que las transformaciones a formato BDD (Gherkin) se generen limpias y sin datos faltantes.

## [0.6.62] - 2026-05-22

### Corregido

- Selección de pasos persistente: Al preparar la conversión a Gherkin, la lista de acciones seleccionadas ya no se restablecerá de forma inesperada si desmarcas elementos o utilizas la opción «Excluir todas».

## [0.6.61] - 2026-05-22

### Añadido

- Colaboración en equipo: Ahora puedes exportar e importar de forma segura la base de conocimiento y el entrenamiento de la IA local, facilitando la unificación de criterios de automatización entre compañeros de trabajo.
- Historial de novedades integrado: Se añadió un acceso directo para consultar este registro de mejoras directamente desde el panel de Configuración → Acerca de.

### Cambiado

- Privacidad y protección avanzada: La memoria de aprendizaje de tu IA local ahora se almacena de forma completamente cifrada en el disco duro, blindando la propiedad intelectual de tus flujos de negocio.
- Editor manual asistido: El editor interactivo de escenarios BDD ahora se habilita de forma automática tras el tercer intento de conversión asistida, permitiéndote tomar el control total y refinar el resultado a tu gusto.
- Pantalla de información estilizada: Se simplificó la sección Acerca de para mostrar de forma limpia la versión actual del producto y el indicador de estado de la fase Beta.

## [0.6.50] - 2026-05-21

### Añadido

- Navegación mejorada: Se incluyó un botón de Regresar al seleccionar proyectos dentro del flujo de grabación para evitar tener que reiniciar el asistente.
- Evidencias en video automáticas: El sistema ahora captura automáticamente el video de la pantalla en tiempo real cuando realizas grabaciones en aplicaciones de escritorio (Legacy) o utilizando el emulador móvil.

### Cambiado

- Asistente de entorno móvil simplificado: El diagnóstico de preparación para pruebas móviles se reorganizó en una sección colapsable mucho más limpia, con alertas claras e instrucciones paso a paso para resolver fallos de entorno.

### Corregido

- Se optimizó la fluidez general al interactuar con la pestaña de automatización móvil y se solucionaron errores visuales en la generación de la vista previa de las conversiones.

## [0.6.30] - 2026-05-21

### Añadido

- Detección inteligente de dispositivos: El sistema ahora detecta automáticamente cualquier dispositivo físico Android conectado por USB o los emuladores instalados en el equipo.
- Control de emuladores integrado: Nueva interfaz que te permite iniciar, pausar y detener tus dispositivos virtuales Android directamente desde la pestaña móvil de ELIA, sin necesidad de abrir herramientas externas.
- Gestión automática de servicios móviles: El motor de automatización móvil se inicializa de forma transparente en segundo plano al arrancar una sesión de grabación.

### Corregido

- Se incrementó drásticamente la estabilidad y se mejoraron los mensajes de alerta cuando el entorno local carece de los componentes necesarios para la automatización móvil.

## [0.5.30] - 2026-05-20

### Corregido

- Se solucionó una discrepancia visual para asegurar que la versión interna de la interfaz coincida exactamente con la compilación del instalador de Windows.
- Se corrigió un comportamiento en las grabaciones web, asegurando que la ventana del navegador integrado se abra maximizada de forma fiable en cada sesión.

## [0.5.20] - 2026-05-20

### Añadido

- Información de activación: Opción para consultar bajo demanda la huella digital técnica y los detalles de tu licencia una vez que la clave ha sido activada en el equipo.

## [0.5.0] - 2026-05-20

### Añadido

- Centro de Configuración unificado: Nueva estructura dividida por pestañas (General, Inteligencia, Licencia, Conectores y Acerca de) para centralizar todas tus preferencias en un solo lugar.
- Optimización inteligente de hardware: El panel de configuración de IA ahora analiza automáticamente las capacidades de procesamiento y gráficos de tu equipo para sugerir el rendimiento óptimo del modelo local.
- Escudo de comprobación web: Se añadieron verificaciones de seguridad automatizadas previas al lanzamiento del navegador para asegurar que las sesiones de grabación inicien limpias y libres de bloqueos.

### Cambiado

- Gestión de licencias simplificada: La interfaz de validación se integró completamente dentro del menú de configuración global, ofreciendo mensajes visuales mucho más claros sobre el estado de la suscripción.
