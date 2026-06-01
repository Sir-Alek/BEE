# Changelog

Todos los cambios notables de ELIA se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones usan [Semantic Versioning](https://semver.org/lang/es/).

## [0.9.66] - 2026-05-28

### Añadido

- Planes de suscripción **Basic**, **Professional** y **Enterprise** con mapa de features por tier (Web, API HTTP, Doc-to-BDD, Postman/suites, Locust, Móvil, Legacy, publishers y Team Memory Crypto).
- Claves de licencia v3 por tier (`ELIA-V3-{BASIC|PRO|ENT}-{duración}-{issue_ts}-{firma}`) y clave beta global sin huella (`ELIA-BETA-GLOBAL-*`).
- Beta plug-and-play: canal `ELIA_CHANNEL=beta`, caducidad fija embebida (30-jun-2026), guardia temporal (reloj de red + ancla anti-retroceso) y pantalla de fin de beta.
- Modal comercial de upselling, badges Pro/Enterprise y bloqueos parciales en la pestaña de pruebas API.
- Endpoint `/api/entitlements` y enriquecimiento de `/api/modules/status` y `/api/license/status`.

### Cambiado

- Los módulos ya no dependen solo de flags M/L: cada feature se valida según el tier activo (backend y UI).
- `doc_to_bdd` deja de estar incluido en cualquier licencia base; requiere Plan Professional o superior.
- Fecha límite beta hardcodeada (sin override por variable de entorno) para evitar bypass de caducidad.

### Corregido

- Compilación Cython de `elia_license.py` (código inalcanzable y `del` sobre parámetros).
- Closure `on_key_press` en grabación Legacy (`nonlocal last_event_emit`).

## [0.9.65] - 2026-05-28

### Añadido

- Conversión inteligente de documentos a BDD: Integración de capacidades avanzadas en el motor de IA local, que ahora utiliza un razonamiento estructurado paso a paso («Análisis Previo») para interpretar la documentación de negocio y transformarla con extrema precisión en escenarios Gherkin limpios y estandarizados.
- Modos de razonamiento ajustables para la IA: Se incorporaron perfiles de procesamiento interno que permiten alternar entre una conversión directa y rápida, o un análisis profundo en dos fases diseñado para desglosar flujos de negocio altamente complejos.
- Captura web optimizada para Inteligencia Artificial: Al grabar interacciones en el navegador, el sistema ahora genera un índice optimizado que aísla y simplifica únicamente los elementos con los que se puede interactuar. Esto permite que la IA procese la página web con mayor velocidad y con un menor consumo de memoria del equipo.
- Estrategias avanzadas de selectores: El motor de captura ahora clasifica y determina con mayor rigor el tipo de selector más estable (ID, CSS, XPath, entre otros), generando automáticamente rutas de respaldo (fallbacks) en las páginas de objetos para asegurar que tus pruebas no se rompan ante cambios en la interfaz.
- Optimización de capturas en flujos móviles: Esta misma tecnología de indexación inteligente de elementos interactivos se aplicó a las sesiones de grabación en dispositivos móviles, mejorando drásticamente la comprensión de la IA sobre la estructura de las pantallas de la aplicación.
- Historial de novedades más ágil: El panel interactivo «Ver novedades» dentro de la sección Acerca de se optimizó para mostrar de forma directa y resumida únicamente las últimas 5 versiones del producto, garantizando una lectura rápida y enfocada en lo más reciente.

### Cambiado

- Procesamiento de documentos más flexible: El convertidor de requerimientos ahora cuenta con una mayor libertad de análisis contextual antes de estructurar el formato definitivo del escenario, lo que reduce errores de interpretación y mejora la calidad del lenguaje de negocio generado.
- Asistente de autoreparación de selectores mejorado: El motor de recuperación ahora prioriza el nuevo índice interactivo y evalúa múltiples estrategias de combinación en lugar de analizar código estructural genérico. Esto incrementa de forma notable la precisión al sugerir selectores preferidos y robustece la estabilidad de tus scripts de automatización.

## [0.9.60] - 2026-05-28

### Añadido

- Diseño avanzado para pruebas de servicios: Nueva interfaz con vista dividida (tipo Maestro-Detalle) para la gestión de API. Ahora dispones de un panel lateral dedicado para explorar tus escenarios, importaciones y capturas, junto con un espacio de trabajo central organizado en pestañas para alternar rápidamente entre la configuración del Entorno y los detalles de la Petición.

### Cambiado

- Organización visual optimizada: Se reestructuró la lógica interna de los paneles de API para ofrecer una navegación mucho más limpia, manteniendo el acceso directo a las pruebas de carga sin alterar tus flujos de trabajo existentes.

## [0.9.55] - 2026-05-28

### Añadido

- Explorador de archivos en árbol: En el espacio de ejecución, la lista plana de archivos se reemplazó por un árbol de directorios colapsable y organizado, lo que facilita navegar por carpetas en proyectos grandes de automatización.

### Cambiado

- Diseño de cabecera unificado: Se restauró la distribución original de la barra superior, devolviendo los logotipos principales del producto a la esquina izquierda para una identidad visual más limpia, manteniendo el indicador de asistencia de IA accesible.
- Interfaces más limpias y asistidas: Se eliminaron párrafos e instrucciones explicativas repetitivas en las secciones de automatización de escritorio (Legacy) y pruebas BDD, sustituyéndolas por discretos cuadros de ayuda flotantes (tooltips) que aparecen al pasar el cursor sobre las etiquetas de los campos.

## [0.9.51] - 2026-05-28

### Añadido

- Componentes de interfaz estandarizados: Se introdujo una nueva capa de diseño global que unifica el estilo de los menús de pestañas, las barras de herramientas secundarias y los avisos de alerta visuales según la importancia del mensaje.
- Monitor de estado de la IA: Se añadió un indicador inteligente en la barra superior que te muestra con un clic el estado de disponibilidad del modelo local y te ofrece un acceso directo a sus ajustes avanzados.
- Flexibilidad en pruebas móviles: Nuevas opciones dentro del asistente móvil que te permiten elegir cómodamente si deseas automatizar una aplicación ya instalada, cargar un archivo ejecutable (.APK), o introducir manualmente el número de serie de tu dispositivo conectado.

### Cambiado

- Diagnóstico móvil simplificado: Los banners de verificación previa se fusionaron en un único panel colapsable de Diagnóstico de conexión que cambia de color de forma inteligente según la prioridad de la alerta, moviendo los textos largos a ayudas flotantes.
- Flujos de trabajo despejados: Se removieron los bloques de texto repetitivos sobre privacidad de inteligencia local en las ventanas de captura Web y Escritorio para agilizar la interacción.
- Asistente de requerimientos mejorado: Se organizaron los paneles de conexión con plataformas externas en una barra secundaria estilizada y se destacó el botón de acción principal para procesar y convertir textos a escenarios BDD con un solo clic.
- Visibilidad en pruebas de carga: Se hicieron visibles las etiquetas de control principales (Usuarios, Tasa de incremento y Duración) sobre los campos del panel de rendimiento.

## [0.9.50] - 2026-05-28

### Añadido

- Publicación multi-destino de requerimientos: Tras revisar tus escenarios Gherkin generados, ahora puedes activar un panel opcional para sincronizar tus pruebas directamente hacia múltiples plataformas empresariales. Es totalmente compatible con repositorios Git (GitHub, GitLab, Azure), Jira clásico, Jira Xray, ValueEdge y exportación a archivos locales.
- Gestión extendida de conectores: El menú de configuración global ahora incluye campos avanzados de sincronización y perfiles optimizados para automatizar las credenciales de publicación predeterminadas.

### Cambiado

- Flujo de trabajo segmentado: Se separó explícitamente el proceso de generación de escenarios BDD del flujo de exportación final, permitiéndote revisar el resultado antes de enviarlo a tus plataformas externas.
- Migración transparente de configuraciones: Tus perfiles de conexión anteriores se actualizan de forma automática al iniciar la aplicación para hacerlos compatibles con las nuevas funciones sin que pierdas tus datos guardados.

## [0.9.43] - 2026-05-28

### Añadido

- Modo de navegador visible: Se añadió la opción interactiva «Mostrar navegador» en el ejecutor web, permitiéndote ver en pantalla el comportamiento físico de Chrome durante las ejecuciones automatizadas (manteniendo el modo oculto por defecto).

### Cambiado

- Se mejoraron las instrucciones de asistencia en el editor interactivo para aclarar el funcionamiento de los filtros de ejecución frente a la edición directa del código de tus escenarios.

## [0.9.42] - 2026-05-28

### Añadido

- Análisis de rendimiento enriquecido: Las pruebas de carga ahora incluyen métricas estadísticas avanzadas (percentiles de respuesta, resúmenes agregados y un registro histórico local de ejecuciones) que te permiten comparar el rendimiento entre distintas corridas directamente desde la interfaz.
- Integración nativa avanzada: El sistema ahora detecta y limpia peticiones duplicadas al importar capturas de navegación web y sincroniza automáticamente la dirección web base hacia tus entornos de pruebas de API.

### Cambiado

- El motor de importación de flujos ahora muestra contadores detallados de elementos procesados u omitidos, y la exportación de reportes de rendimiento genera formatos visuales enriquecidos de forma predeterminada.

## [0.9.41] - 2026-05-28

### Cambiado

- Nueva organización en Pruebas de API: La sección de servicios se reestructuró en dos subpestañas especializadas para reflejar el flujo de trabajo estándar de ingeniería: un constructor visual para peticiones individuales e importaciones (Postman), y un panel de rendimiento y métricas para ejecuciones masivas (JMeter-lite / Locust). Ambas comparten de manera inteligente la barra de proyectos, abriendo las vistas adecuadas automáticamente según la acción que realices.

## [0.9.40] - 2026-05-28

### Añadido

- Ejecutor de suites de servicios completo: Nueva funcionalidad para lanzar secuencias de escenarios de API en orden consecutivo con resúmenes de éxito/fallo en tiempo real y la opción de decidir si la ejecución debe continuar o detenerse ante un fallo.
- Intercambio dinámico de datos (Correlación): El sistema ahora puede extraer información clave de las respuestas de una petición (como encabezados o datos de contenido) y guardarla en variables de sesión para reutilizarla automáticamente en los pasos siguientes de la prueba.
- Pruebas basadas en datos (Data-Driven): Ahora puedes vincular archivos CSV de datos locales para que tus secuencias de API se ejecuten cíclicamente utilizando los valores de cada fila de forma parametrizada.
- Validaciones avanzadas de API: Se incorporaron reglas estrictas de verificación en la interfaz que te permiten evaluar tiempos máximos de respuesta permitidos, buscar patrones de texto o comprobar estructuras de contenido específicas en las respuestas del servidor.
- Panel de monitoreo de carga en vivo: Gráficas y métricas de rendimiento en tiempo real durante las pruebas de carga, permitiéndote configurar el peso de frecuencia de cada escenario y las tasas de usuarios desde el propio panel.

### Cambiado

- El motor de pruebas de carga ahora distribuye las tareas asignando de forma proporcional el peso configurado a cada escenario desde la interfaz.

## [0.9.32] - 2026-05-28

### Añadido

- Evidencias de API bajo demanda: Se agregaron botones para exportar resúmenes en formato PDF o JSON de tus peticiones de servicios individuales únicamente cuando lo solicites, asegurando que las consultas rápidas de desarrollo no llenen el equipo de archivos innecesarios.
- Reportes de carga controlados: Las ejecuciones de rendimiento ahora operan de forma limpia en memoria por defecto y exponen una casilla opcional para generar reportes detallados en PDF al finalizar la prueba si el usuario lo activa.
- Panel de respuestas ampliado: Se mejoró la sección de resultados incluyendo una sección desplegable dedicada exclusivamente a inspeccionar los encabezados (headers) devueltos por el servidor.

### Cambiado

- Se optimizó la edición de tablas de encabezados globales y de peticiones, añadiendo botones de eliminación directa para cada fila de forma ágil.
- Las pruebas de rendimiento ahora reservan el uso de disco exclusivamente para cuando decides exportar de manera explícita un reporte de evidencias.

### Corregido

- Se solucionó un problema técnico de bucle interno que provocaba congelamientos visuales al intentar dar de alta proyectos de API nuevos.

## [0.9.31] - 2026-05-28

### Añadido

- Ejecución directa de servicios: El módulo de API se rediseñó por completo para permitir consultas HTTP directas e instantáneas sin depender de la generación previa de scripts de automatización tradicionales.
- Gestor de entornos dinámicos: Ahora puedes crear perfiles de entorno por proyecto para intercambiar variables automáticas dentro de tus direcciones web, encabezados y cuerpos de mensajes.   
- Fusión inteligente de encabezados: Permite definir encabezados globales para todo el proyecto que se combinan automáticamente con los específicos de cada petición, dándole prioridad a estos últimos.
- Importador de colecciones estándar: Soporte nativo para cargar colecciones de Postman y especificaciones OpenAPI (Swagger) transformándolas directamente en escenarios de prueba interactivos y reutilizables.

### Cambiado

- Los nuevos proyectos de API se inicializan con un enfoque directo y limpio enfocado en el constructor visual, reemplazando las antiguas estructuras de archivos por un panel de control interactivo con respuestas integradas.

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
