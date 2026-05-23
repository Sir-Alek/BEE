# Changelog

Todos los cambios notables de ELIA se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones usan [Semantic Versioning](https://semver.org/lang/es/).

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
