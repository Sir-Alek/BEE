# Changelog

Todos los cambios notables de ELIA se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y las versiones usan [Semantic Versioning](https://semver.org/lang/es/).

## [0.10.13] - 2026-07-01

Consolidación de asistentes de inducción (plantillas Web y de servicios), diagnóstico inteligente de ejecuciones, guías de inicio rápido para entornos móviles y de escritorio, junto con optimizaciones clave de usabilidad en la consola de resultados, paneles de API y el explorador de archivos local.

### Añadido

- Catálogo de plantillas de proyecto de inicio rápido: Modelos empaquetados listos para usar que incluyen flujos típicos de inicio de sesión web basados en portales de prueba, verificaciones rápidas de servicios simulados de integración y entornos combinados completos. Incorpora un asistente de creación guiada con una lista de verificación posterior y validación automática de datos para garantizar proyectos estables y listos para operar desde el primer segundo.
- Administrador de proyectos unificado: Nuevas opciones interactivas para renombrar, eliminar o explorar directamente la ubicación física de tus proyectos locales en todas las plataformas (Web, Móvil, Escritorio y API), añadiendo etiquetas visuales especiales para identificar rápidamente aquellos creados a partir del catálogo.
- Centro de diagnóstico unificado tras fallos: Al interrumpirse o fallar una prueba automatizada, la consola de ejecución ahora despliega un panel de diagnóstico inteligente que detalla con precisión el escenario afectado, el paso exacto de negocio (Gherkin) donde ocurrió el error, el motivo principal del fallo, el tipo de alerta y las notas de asistencia técnica. Incluye además una vista previa en miniatura de la captura de pantalla del error y accesos directos estructurados para inspeccionar los registros históricos de ejecuciones guardados.
- Historial de ejecuciones recientes por proyecto: Nuevo panel integrado en la consola que almacena y organiza los últimos 5 resultados de tus corridas de prueba. Al hacer clic en cualquier entrada de este historial, la interfaz recargará instantáneamente el estado visual completo y el diagnóstico guardado de esa ejecución específica.
- Guías de inicio rápido para entornos móviles y de legacy: Manuales de inducción ágiles integrados de forma nativa en las pestañas de grabación móvil y de escritorio de Windows. Incluye el acceso directo «Guía rápida», paneles interactivos que detallan visualmente los pasos del flujo y tarjetas de asistencia contextuales si no hay proyectos creados, incorporando la opción «No volver a mostrar» para recordar tus preferencias y mantener despejada la pantalla. El área de trabajo de estas plataformas queda optimizada guiando al usuario de forma natural hacia el flujo recomendado de grabación, conversión a escenarios de negocio y ejecución.
- Control flexible de asistencia visual: Nueva opción dentro del menú de Configuración → General para activar o desactivar las guías de inicio rápido de la interfaz, acompañada de un botón interactivo para restablecer las tarjetas de ayuda que hayas ocultado previamente, sin alterar el contenido de los manuales de usuario.

### Cambiado

- Reorganización inteligente del menú principal: La pestaña de Pruebas de API se posiciona ahora en segundo lugar de forma estratégica dentro de la barra de navegación debido a su gran volumen de herramientas y uso frecuente, optimizando el flujo de trabajo diario.
- Flujo automatizado para proyectos de demostración: Al inicializar plantillas de servicios o entornos combinados, el sistema preselecciona automáticamente el proyecto y la colección predeterminada, cargando de inmediato el escenario de prueba en el cliente visual. En proyectos integrados de automatización, la sección de servicios queda enlazada perfectamente entre los menús principales para agilizar la navegación.
- Interfaz de inducción móvil y legacy simplificada: Se removieron opciones y mensajes redundantes relacionados con la creación de proyectos basados en catálogos externos para guiar al usuario de forma natural hacia la grabación interactiva de flujos reales y su posterior transformación a proyectos automatizados (BDD).
- Notificaciones contextuales emergentes: Los avisos flotantes del sistema (como al abrir carpetas de resultados, acceder a consolas de diagnóstico o confirmar tareas) ahora aparecen exactamente debajo del botón presionado con una duración optimizada de 3 segundos, evitando que los mensajes queden fuera de vista al desplazarte por pantallas extensas.
- Alertas de confirmación automatizadas: Las confirmaciones de operaciones en la pestaña de servicios (como guardar de escenarios o importar colecciones) ahora se ocultan solas tras unos segundos para mantener despejada tu área de trabajo.
- Indicador de sincronización en selectores: El menú de proyectos de servicios ahora muestra un indicador de carga y permanece protegido hasta recibir la lista actualizada del servidor, previniendo selecciones erróneas o visualizaciones incompletas al abrir la pestaña de forma inmediata.
- Consola de ejecución enfocada en la resolución de errores: Ante una interrupción en una prueba de comportamiento, el sistema prioriza y te vincula directamente al registro específico de ese escenario e integra el botón unificado «Abrir carpeta de resultados» para acceder cómodamente a tus logs, reportes PDF y capturas de pantalla de evidencias en un solo lugar.
- Exploración de proyectos optimizada: La función de «Abrir carpeta» ahora te redirige de forma directa al directorio raíz local exacto de tu proyecto según la plataforma de automatización seleccionada.
- Mantenimiento automatizado de registros de sistema: El historial general de eventos de la aplicación ahora implementa un ciclo de rotación optimizado que conserva únicamente un máximo de 7 días de registros en el equipo, protegiendo el espacio de almacenamiento local de tu computadora.
- Auditoría de fallos web más limpia: El motor de diagnóstico web se mejoró para evitar consultas de estado de la interfaz si el navegador ya fue cerrado por el usuario o el sistema operativo, eliminando alertas o mensajes técnicos confusos en la consola y concentrándose únicamente en la causa raíz que provocó el fallo de la prueba.

### Corregido

- Protección de datos en colecciones de catálogo: Se corrigió un comportamiento que sobrescribía accidentalmente las configuraciones de servicios al dar de alta proyectos basados en plantillas, asegurando que los escenarios preconfigurados y las carpetas por defecto convivan de forma completamente segura.
- Estabilización de proyectos de demostración: Se validaron por completo los modelos de ejemplo, asegurando que integren de forma nativa sus conjuntos de datos estructurados, compartan pasos unificados y ejecuten verificaciones de consistencia para garantizar corridas iniciales exitosas.
- Integridad total en reportes PDF: Los reportes analíticos finales ahora ordenan cronológicamente todas tus capturas de pantalla de forma numerada, anexan limpiamente las imágenes tomadas en el momento exacto del error y resuelven correctamente la ubicación real de las especificaciones de negocio vinculadas.
- Compatibilidad visual en paneles de diagnóstico: La pantalla de resultados ahora es tolerante ante registros de ejecuciones antiguas, evitando errores visuales o cuadros vacíos si los reportes históricos carecen de datos de evidencia avanzados.

## [0.10.11] - 2026-06-28

### Añadido

- Asistente de configuración de dispositivos virtuales: (Exclusivo de ELIA Architect). Nuevo flujo guiado que inspecciona automáticamente tu entorno móvil, asiste en la aceptación de licencias de desarrollo y gestiona la instalación automatizada de emuladores locales mediante plantillas optimizadas: Estándar (emulación de dispositivos modernos de última generación) y Ligera (para equipos con recursos de hardware medidos). Todo el proceso se ejecuta de forma segura en segundo plano, mostrando un indicador de progreso visual directo en la interfaz.
- Compatibilidad y configuración manual de entornos móviles: Disponible en todos los planes comerciales. Si la detección automatizada no localiza las herramientas del sistema, la interfaz despliega un panel integrado que permite ingresar rutas personalizadas, localizar el ejecutable oficial mediante el explorador de archivos nativo del sistema operativo o guardar la ubicación preferida para futuras sesiones de trabajo de forma rápida.
- Centro de gestión del "Entorno local": Nueva pestaña dedicada dentro del menú de configuración para definir y centralizar las rutas de todas tus herramientas clave de automatización (servicios móviles, emuladores, navegadores web y controladores). Cada campo incorpora opciones para detección automática, ajustes personalizados, exploración de archivos, pruebas de conectividad individuales y un botón global para Ejecutar diagnóstico, el cual realiza una validación completa y simultánea de todos tus componentes de prueba web y móvil.
- Detección inteligente extendida: Optimizamos el motor de búsqueda de entornos móviles en Windows. Ahora el sistema rastrea instalaciones avanzadas (como las gestionadas por cajas de herramientas de desarrollo o variables del sistema) y, en caso de no encontrarlas, despliega un listado detallado de las rutas inspeccionadas para facilitar enormemente la asistencia de soporte.
- Diagnósticos móviles más precisos: El asistente de preparación ahora diferencia claramente entre el catálogo de emuladores instalados y los dispositivos virtuales conectados en tiempo real. Además, verifica la presencia de los componentes de comandos esenciales y guía amigablemente al usuario hacia el asistente de configuración si detecta que la lista de dispositivos virtuales está vacía.
- Asistencia guiada para el plan ELIA Tester: Al intentar acceder al asistente de automatización de dispositivos virtuales desde el plan Tester, la aplicación mostrará una ventana informativa clara explicando que la creación automática es una característica avanzada de ELIA Architect. Para no interrumpir tu flujo de trabajo, el panel ofrece accesos directos inmediatos para abrir el entorno de desarrollo externo, gestionar las rutas manualmente en la pestaña de entorno local o contactar al equipo para una actualización de plan.
- Sincronización automática de emuladores: Tras concluir la creación automatizada en el plan Architect, el sistema valida inmediatamente que el nuevo emulador esté disponible y lo deja preseleccionado en el menú desplegable de la pantalla de automatización móvil para que puedas usarlo al instante.

### Cambiado

- Jerarquía inteligente de configuraciones: Se refinó el orden de prioridad para la lectura de herramientas: el sistema dará prioridad absoluta a los ajustes manuales definidos en el menú de Entorno local, seguido de las variables personalizadas del sistema operativo y, por último, los métodos de detección automática del producto.
- Herramientas de entorno accesibles en todos los niveles: Los accesos directos para abrir el panel de desarrollo externo y realizar comprobaciones rápidas de estado ahora son visibles en todas las suscripciones, manteniendo la automatización de la creación de dispositivos optimizada para la edición avanzada.
- Integración avanzada del asistente: Las capacidades del asistente móvil ahora interactúan de forma directa con tu entorno de desarrollo, detectando qué herramienta configuró el espacio de trabajo e identificando alternativas automáticas de ubicación cuando faltan componentes principales.

### Corregido

- Mensajes de estado interactivos en emuladores: Se solucionó un comportamiento silencioso en el botón de inicialización; ahora la interfaz muestra alertas claras y explicativas si intentas arrancar un emulador sin haber seleccionado un dispositivo virtual o si tu catálogo local no cuenta con componentes instalados.
- Claridad en el estado de dispositivos conectados: Corregimos las alertas duplicadas para diferenciar de forma precisa cuando tu catálogo de emuladores está vacío frente a cuando ya cuentas con un dispositivo virtual activo y vinculado en segundo plano, desplegando banners informativos dinámicos de color según la situación.
- Consistencia visual en cargas: Se unificó el indicador de espera para la comprobación del entorno móvil y se alinearon los mensajes de asistencia transitorios con el diseño global del resto de los módulos de la aplicación.

### Comercial

- Gestión de dispositivos virtuales por niveles: La creación y orquestación automática de entornos virtuales móviles es de uso exclusivo para el plan ELIA Architect (canal Beta incluido). Los usuarios de ELIA Tester conservan el acceso directo al entorno externo, el panel de gestión de entorno local y la configuración manual de rutas.

### Robustez del Sistema

- Controles de calidad internos incrementados: Expandimos la cobertura de validaciones automatizadas internas sobre el sistema de resolución de rutas, la detección inteligente de entornos de desarrollo avanzados y los mecanismos de creación de emuladores móviles para garantizar un despliegue altamente confiable antes del lanzamiento.

## [0.10.10] - 2026-06-27

### Añadido

- Validación progresiva de accesos por nivel: Se implementó un nuevo motor de permisos que gestiona de manera fluida la carga de la interfaz en fases ordenadas. El núcleo principal de tu plan se habilita inmediatamente en cuanto se confirma la validez de la licencia, mientras que las herramientas avanzadas muestran un estado de transición optimizado en lo que reciben la configuración del servidor, evitando bloqueos visuales en el arranque.
- Componentes visuales de acceso unificados: Introducción de elementos de control integrados (como indicadores de carga inteligente, paneles informativos de nivel y pantallas claras de asistencia) para guiar al usuario de forma transparente sobre las funciones disponibles según su suscripción activa.
- Protección de sincronización de licencias: Nueva memoria caché local que invalida de forma automática configuraciones antiguas al detectar un cambio de plan, asegurando que los permisos visuales de la interfaz coincidan exactamente con el nivel de suscripción vigente y previniendo elevaciones de privilegios erróneas.
- Exploración de escenarios ultra-rápida: Se añadió un índice optimizado de pruebas de servicios que lee metadatos resumidos en lugar de procesar archivos individuales completos. Esto acelera notablemente la velocidad de respuesta en proyectos grandes con un alto volumen de colecciones.
- Navegación asistida en el Cliente API: Incorporamos un sistema de carga visual en el panel lateral que se activa mientras se obtienen los escenarios de servicios, sincronizado de forma de un endpoint dedicado para filtrar búsquedas por colección.
- Preferencias de lenguaje y aprendizaje inteligente: Nuevo panel dentro del menú de Configuración → Inteligencia para configurar el uso preferente de palabras clave Gherkin en inglés, adaptando el sistema para asimilar correcciones automáticas basadas en tus reintentos de edición de manera personalizada.
- Control avanzado de la memoria de la IA local: Ahora puedes vaciar, exportar de forma cifrada o importar (reemplazar o fusionar) tus ejemplos de aprendizaje directamente desde la configuración de la interfaz. El sistema respeta rigurosamente tus preferencias y guarda las correcciones únicamente cuando decides realizar modificaciones explícitas en tus flujos de negocio.
- Herramientas de diagnóstico de interfaz: Se añadió un comando de autochequeo ejecutable en el entorno de diseño para validar el comportamiento correcto de las fases de acceso visual.

### Cambiado

- Arranque limpio y libre de avisos prematuros: Durante la verificación inicial de la licencia, la interfaz se mantiene en un estado neutro y estético sin desplegar alertas visuales o mensajes comerciales invasivos. Las opciones de actualización aparecen exclusivamente cuando el estado del plan está plenamente confirmado en el equipo y una función es explícitamente denegada.
- Control inteligente de acciones en pantalla: Las funciones principales de grabación, conversión, gestión de requerimientos y pruebas de API ahora responden de forma coordinada a la fase de validación del sistema, manteniéndose protegidas durante la comprobación inicial y habilitándose de inmediato al confirmar un acceso válido.
- Modo desconectado con respaldo automático: Si la sincronización de red con el servidor de módulos llega a interrumpirse, la aplicación desplegará un banner informativo de uso de la última configuración local conocida en memoria. El sistema aplicará las restricciones correspondientes a tu nivel y realizará reintentos de conexión automáticos en cuanto la ventana recupere el foco de atención del usuario.
- Acceso inmediato al programa Beta: Optimizamos el proceso de verificación para el canal de pruebas, permitiendo un ingreso instantáneo a todas las capacidades y herramientas avanzadas sin tiempos de espera intermedios entre módulos.
- Estandarización de palabras clave Gherkin: El convertidor de requerimientos y el motor de captura web ahora priorizan la generación de términos de negocio (Given/When/Then) en inglés para alinearse perfectamente con los estándares globales de automatización, manteniendo la flexibilidad de conservar los textos descriptivos de los pasos en español.

### Corregido

- Eliminación de falsos bloqueos al inicio: Se corrigió un comportamiento visual intermitente para asegurar que los indicadores de restricción u opacidad no aparezcan prematuramente mientras el sistema procesa la respuesta de activación al arrancar la aplicación.
- Consistencia estricta en cambios de nivel: Se solucionó un desfase en la memoria local para garantizar que la interfaz refleje de inmediato cualquier ajuste o reducción de nivel de suscripción contratado, evitando accesos indebidos por encima del plan confirmado.
- Reducción de latencia en proyectos masivos: Se resolvió la lentitud de lectura en disco al explorar grandes volúmenes de servicios gracias a la optimización del nuevo indexador y la eliminación de consultas redundantes en el almacenamiento local.

### Robustez del Sistema

- Verificación de seguridad y estabilidad reforzada: Ampliamos los de control automatizados internos para validar los ciclos de aprendizaje de la IA, el indexador de servicios masivos, los estilos de Gherkin y el motor de permisos de usuario. Asimismo, el núcleo de seguridad de la aplicación actúa como la autoridad final, bloqueando cualquier ejecución real en segundo plano ante accesos inválidos, independientemente de los estados de transición visual de la interfaz.

## [0.10.0] - 2026-06-27

### Añadido

- Nuevo motor de IA local adaptativo (Perfiles Standard y Lite): Se renovó por completo el núcleo de inteligencia artificial local, introduciendo los perfiles de rendimiento ELIA Standard y ELIA Lite. La aplicación ahora detecta automáticamente la memoria RAM de tu equipo para asignarte el perfil óptimo (Standard para equipos con más de 8 GB; Lite para configuraciones de 8 GB o menos). El perfil Standard alterna inteligentemente los recursos en memoria según la tarea activa para maximizar la precisión, mientras que el perfil Lite unifica los procesos para asegurar una fluidez total en equipos con recursos moderados.
- Asistente de configuración inicial: Nuevo asistente interactivo para el primer arranque que te guía paso a paso en la descarga e instalación segura de los nuevos componentes de IA desde el repositorio oficial. Cuenta con verificación automática de integridad, detección de copias locales manuales y la opción de «Configurar más tarde». El sistema recuerda tu progreso entre sesiones y omitirá esta ventana de forma transparente una vez que los componentes estén listos.
- Panel de Inteligencia renovado: El menú de Configuración → Inteligencia ahora permite consultar tu perfil recomendado, gestionar descargas asistidas y reabrir el asistente de configuración en cualquier momento. El estado actual se muestra de forma clara y limpia (Lite/Standard) sin sobrecargar la interfaz con nomenclaturas técnicas complicadas.
- Gestor de descargas optimizado: Se incorporó un sistema de transferencia en segundo plano que te permite descargar las actualizaciones del motor de inteligencia sin interrumpir tus flujos de trabajo, ofreciendo un monitoreo de progreso preciso en tiempo real.

### Cambiado

- Evolución masiva del motor de Inteligencia Artificial: Esta versión introduce una actualización mayor en el núcleo de IA local que sustituye al motor anterior por completo. Los archivos previos ya no serán utilizados, por lo que es necesario descargar los componentes del nuevo perfil (a través del asistente, el menú de configuración o mediante los pasos de copia manual detallados en el archivo técnico complementario para la campaña de Julio 2026).
- Políticas inteligentes de consumo de hardware: Para garantizar que tu computadora nunca sufra ralentizaciones, el perfil Standard requiere un mínimo de 5 GB de memoria libre y el perfil Lite exige 4 GB libres para operar. Si tu equipo se encuentra temporalmente por debajo de estos límites, la IA se pausará automáticamente y activará de forma segura nuestro sistema de respaldo heurístico tradicional.
- Distribución eficiente de tareas de QA: El sistema ahora enruta automáticamente cada acción (como la conversión de documentos a BDD, la autoreparación de selectores o las validaciones de API) hacia el componente interno más eficiente según tu perfil activo, incorporando un indicador visual de procesamiento avanzado («Pensando») únicamente en tareas de análisis profundo.
- Interfaz totalmente neutral y profesional: Se unificaron todos los textos, alertas y mensajes del sistema para utilizar un lenguaje neutral enfocado en las capacidades del producto, manteniendo la pantalla limpia de marcas comerciales externas y concentrando las especificaciones detalladas en la documentación técnica de soporte.

### Corregido

- Compatibilidad garantizada con versiones previas: Se integraron capas transparentes de compatibilidad interna para asegurar que todos los proyectos de automatización, escenarios y flujos creados bajo el motor anterior sigan operando y delegando sus tareas de forma perfecta hacia el nuevo núcleo.

### Robustez del Sistema

- Validaciones de estabilidad ampliadas: Se expandió la cobertura de controles de calidad internos para certificar la precisión en la lectura de memoria RAM, la estabilidad del asistente de configuración y el comportamiento correcto de las políticas de respaldo automático antes del despliegue masivo.

## [0.9.78] - 2026-06-26

### Añadido

- Historial con progreso en vivo de secuencias: Se incorporó un registro histórico detallado para las suites funcionales de servicios que muestra el avance en tiempo real a medida que se ejecutan los pasos de la prueba.
- Generación retroactiva de informes de rendimiento: Ahora puedes exportar reportes analíticos estructurados en PDF y HTML a partir de simulaciones de carga guardadas en tu historial, lo que permite consultar los documentos de evidencias bajo demanda sin necesidad de volver a ejecutar la prueba de estrés.
- Asistente de diagnóstico previo para carga distribuida: Añadimos una verificación de preparación rápida y orientativa para entornos masivos distribuidos en red, validando la estabilidad antes de lanzar la simulación de tráfico masiva.
- Visualizador de respuestas estilizado: El visor del Cliente API ahora aplica un formato automático inteligente y resaltado de colores a los datos devueltos por el servidor, garantizando una inspección de resultados significativamente más rápida y cómoda.
- Buscador integrado en colecciones: Nueva barra de filtrado rápido dentro de la barra de exploración lateral, facilitando la localización instantánea de carpetas, servicios y escenarios específicos en proyectos con altos volúmenes de pruebas.
- Clonación rápida de escenarios: Se introdujo una función interactiva que permite duplicar escenarios de validación existentes con un solo clic, agilizando el diseño de variantes de prueba sobre la misma base.
- Editor avanzado para scripts de servicios: El panel de configuración de interacciones ahora integra herramientas de edición profesional que facilitan la escritura y mejoran la legibilidad de tus scripts de validación.
- Ventanas de confirmación integradas: Reemplazamos las ventanas de alerta nativas del sistema operativo por cuadros de diálogo personalizados que respetan estrictamente la estética y el tema visual activo de la aplicación.
- Importación de servicios más compatible y fiable: Se optimizó drásticamente el motor de interpretación de especificaciones OpenAPI 3, resolviendo referencias internas complejas de esquemas y vinculando de forma transparente los mecanismos de autenticación (como tokens de portador o llaves de API) directamente hacia los encabezados de las peticiones.
- Ampliación de aserciones lógicas: El asistente de scripts extendió sus capacidades de verificación predictiva, permitiendo evaluar inclusiones y equivalencias exactas sobre estructuras y campos de datos complejos.
- Notificaciones preventivas de renovación: Introdujimos un banner visual sutil y descartable en la interfaz que te informará con antelación cuando tu suscripción se encuentre entre 8 y 14 días de concluir, reservando las alertas prioritarias de pantalla únicamente para la última semana de vigencia.
- Persistencia de estado en el espacio de trabajo: Tus direcciones web escritas, códigos en edición y subpestañas activas dentro del Cliente API se mantendrán memorizadas si decides cambiar temporalmente entre los menús principales del panel de control, previniendo cualquier pérdida accidental de tu progreso.

### Cambiado

- Acceso unificado a herramientas de control: La pestaña de «Suites y carga» se mantiene siempre abierta y disponible para consulta. Los módulos de secuencias funcionales, vinculación de archivos de datos y ejecuciones base quedan plenamente habilitados desde el plan ELIA Tester, aplicando indicadores visuales de actualización únicamente sobre los módulos avanzados de simulación de estrés masivo exclusivos del plan ELIA Architect.
- Diseño compacto para selección masiva de escenarios: El catálogo de pruebas para la suite y bloques de rendimiento se reorganizó en una sección colapsable con panel de desplazamiento optimizado. El control para «Seleccionar todos» permanece fijo en pantalla al navegar por la lista, evitando que las colecciones extensas distorsionen el orden o desplacen los botones de acción principales.
- Gestión simplificada de colecciones: Se integró un botón compacto en la barra de exploración lateral para vaciar el catálogo general o remover colecciones importadas de forma directa, acompañado de descripciones de asistencia flotantes según la acción elegida.
- Manual de secuencias de API al alcance: El Cliente API ahora incluye accesos directos para consultar la documentación de scripts desde el propio panel de trabajo, asegurando que cada proyecto guarde automáticamente una copia local del manual para su consulta desconectada.

### Robustez del Sistema

- Controles de calidad internos incrementados: Expandimos la cobertura de validaciones automatizadas internas sobre el motor de condiciones lógicas, el convertidor de esquemas de servicios, el sistema de progreso de históricos y la estabilidad en la gestión de carpetas de API para garantizar un entorno de software altamente confiable antes del despliegue.

## [0.9.77] - 2026-06-21

### Añadido

- Validación de mensajería empresarial: Se incorporó un asistente de comprobación previa para servicios de comunicación rápidos dentro del constructor de flujos. El nuevo botón «Validar reflexión» permite certificar de forma visual que la estructura del servidor sea correcta y compatible antes de lanzar ejecuciones.
- Control inteligente de carga distribuida: Implementamos reglas de validación avanzadas y una guía operativa integrada dentro del panel de rendimiento para configurar simulaciones masivas entre múltiples equipos (master/worker), incluyendo verificaciones automáticas de dependencias en flujos de tráfico mixtos.
- Gestión avanzada de Colecciones de API: Ahora puedes crear y organizar tus escenarios en múltiples colecciones por proyecto. Al importar archivos estándar del mercado o esquemas de servicios, el sistema agrupará las pruebas automáticamente dentro de una carpeta con el nombre del archivo de origen. Incluye botón **Eliminar** en cada colección del sidebar: vacía **General** (borra todos sus escenarios pero la mantiene como contenedor por defecto) o elimina por completo las colecciones importadas. Migración transparente en segundo plano para proyectos existentes.

### Cambiado

- Diagnósticos enriquecidos en simulaciones masivas: La respuesta visual del panel de rendimiento ahora incluye detalles detallados sobre el modo de ejecución y comandos internos, facilitando la auditoría de despliegues distribuidos en red.
- Barra lateral del Cliente API mejorada: Se actualizó el panel lateral organizándolo en un árbol de directorios colapsable por carpetas, con contadores de escenarios interactivos, un selector para elegir el destino al guardar nuevas pruebas y ventanas de confirmación de seguridad antes de remover una colección entera.
- Interfaz nativa y estandarizada: Se optimizaron los textos y títulos de la sección de servicios para adoptar una terminología completamente propia del producto y neutral respecto a marcas de terceros. La compatibilidad total para importar e interpretar formatos estándar del mercado se mantiene intacta bajo el capó.
- Manual de asistencia para scripts de API integrado: Incorporamos accesos rápidos directamente en el Cliente API (a través de los botones «Ver guía de scripts» y «Abrir guía completa») para consultar la documentación técnica de referencia integrada de forma nativa en la pantalla de trabajo, eliminando la necesidad de buscar manuales externos mientras editas tus pruebas.

## [0.9.76] - 2026-06-20

### Añadido

- Plantillas profesionales de rendimiento: Se introdujeron perfiles preconfigurados para pruebas masivas (Carga, Estrés, Picos, Resistencia, Escalabilidad y Volumen). Estas plantillas calculan automáticamente las etapas de incremento de tráfico y configuran intervalos de espera realistas adaptados a cada escenario.
- Panel centralizado de objetivos de calidad: Nueva sección visual en el menú de rendimiento para gestionar tus acuerdos de nivel de servicio (SLA) basados en tiempos de respuesta, porcentajes de error y transacciones por segundo. Centraliza también la asignación de variables vinculadas por archivos de datos y los procesos de simulación distribuida.
- Remoción directa de escenarios: Se incluyeron botones interactivos de borrado rápido para escenarios de API tanto en la barra de exploración lateral como dentro de la pestaña de ejecución de rendimiento.
- Reportes avanzados según perfil de prueba: Los informes analíticos en PDF y HTML ahora adaptan su diseño de forma inteligente al tipo de prueba realizada, incorporando un bloque destacado de aprobación o fallo de objetivos (SLA) y tablas detalladas de rendimiento para auditorías de escalabilidad.
- Historial de simulación enriquecido: El registro histórico de ejecuciones ahora guarda de forma explícita el perfil de carga utilizado y el resultado del cumplimiento de calidad, manteniendo al día tu panel local de comparación de rendimiento.
- Manual técnico de scripts de servicios: Se integró una guía técnica detallada dentro del catálogo de recursos de la aplicación para asistir en el diseño de scripts avanzados basados en lógica compatible con estándares de la industria.

### Cambiado

- Simplificación y evolución de Planes Comerciales: Optimizamos nuestra estructura de suscripciones para ofrecer un licenciamiento más claro y enfocado en roles profesionales. Las categorías anteriores se unifican bajo los nuevos planes ELIA Tester (diseñado para ingenieros de ejecución y automatización base) y ELIA Architect (destinado a arquitecturas empresariales y flujos distribuidos), aplicando una normalización automática y transparente para todas las claves vigentes.
- Simulaciones de tráfico más realistas: El motor de carga masiva ahora permite interpolar variables de forma dinámica en flujos sencillos y realiza una rotación automatizada de las filas de tus archivos de datos durante el estrés, simulando un comportamiento de usuarios virtuales mucho más fiel a la realidad.
- Sincronización ágil entre entornos: Se incrementó la visibilidad del puente de integración en la barra lateral, facilitando la sincronización inmediata de la dirección web base capturada durante tus grabaciones web hacia el entorno de pruebas de API.

## [0.9.75] - 2026-06-19

### Añadido

- Guía interactiva de funciones de automatización: El explorador del área de desarrollo ahora muestra de forma destacada un manual interactivo integrado que documenta el uso correcto y ejemplos prácticos de las funciones de automatización para páginas y elementos de interfaz (Web, Escritorio y captura de evidencias), manteniendo la edición de scripts avanzados accesible en una sección secundaria.
- Autocompletado contextual avanzado: El editor de código ahora ofrece sugerencias de escritura enriquecidas que incluyen resúmenes informativos y la estructura exacta de tus funciones personalizadas, ayudas flotantes al pasar el cursor sobre los archivos y atajos predictivos al importar componentes compartidos.

### Cambiado

- Actualización automática de proyectos: Todos tus proyectos existentes recibirán e de forma transparente este nuevo manual de asistencia técnica al momento de explorar sus archivos.

## [0.9.74] - 2026-06-19

### Añadido

- Trazabilidad avanzada de operaciones: Se implementó un registro estructurado y centralizado para documentar el inicio y fin de todas las tareas del sistema (secuencias de servicios, ejecuciones de rendimiento y flujos de carga masiva), aplicando filtros automáticos para sanitizar y omitir cualquier dato confidencial corporativo.
- Acceso inmediato a registros de soporte: Se añadieron botones directos dentro de los paneles de tareas interrumpidas o consolas fallidas para abrir la carpeta de diagnósticos o inspeccionar el archivo de eventos del sistema al instante.
- Exploración de diagnósticos nativa: Nueva función interna que abre de forma directa el directorio local de registros de ejecución en el explorador de archivos de tu sistema operativo.

### Cambiado

-Ajuste de profundidad en diagnósticos: El nivel de detalle de las alertas y registros de eventos ahora se puede configurar de manera flexible para alternar entre resúmenes generales o seguimientos técnicos exhaustivos.

## [0.9.73] - 2026-06-19

### Añadido

- Inyección dinámica de datos en pruebas de rendimiento: Ahora es posible configurar secuencias de consultas a bases de datos para que se ejecuten automáticamente justo antes de iniciar una prueba de carga. El sistema procesa los datos iniciales e inyecta los resultados en vivo dentro de la simulación de rendimiento.
- Pruebas de carga para servicios de alta velocidad (Plan Enterprise): Las capacidades de simulación de rendimiento masivo se extendieron para dar soporte nativo a protocolos empresariales avanzados de comunicación rápida, interpretando sus estructuras de mensajería y extrayendo variables bajo demanda.
- Selector de flujos integrados en rendimiento: El panel de pruebas de carga permite asociar flujos secuenciales y lógicos completos guardados en lugar de peticiones individuales, desplegando avisos informativos si se detectan pasos avanzados de datos.
- Catálogo de complementos opcionales: Se incluyó un manual de requisitos de soporte técnico para instalar de forma sencilla y bajo demanda los controladores de bases de datos y protocolos de comunicación específicos según las necesidades de tu proyecto.

## [0.9.72] - 2026-06-19

### Añadido

- Guardado y organización de flujos interactivos: Las secuencias diseñadas en el panel de flujos ahora se pueden almacenar y recuperar por proyecto, incorporando alertas de confirmación inteligente para evitar sobrescrituras accidentales.
- Extracción múltiple de variables: Los pasos de bases de datos y servicios avanzados ahora permiten capturar múltiples datos en una sola acción, asociando columnas o respuestas específicas directamente hacia variables reutilizables dentro del flujo.
- Validación previa de complementos: Se añadieron indicadores visuales de estado que confirman si tu entorno local está listo para operar, junto con un botón para realizar comprobaciones rápidas de credenciales de bases de datos sin necesidad de ejecutar toda la suite de pruebas.
- Integración segura con perfiles de entorno: Los formularios de bases de datos ahora sugieren y vinculan automáticamente los usuarios y claves definidos en tus perfiles de entorno activos, previniendo la exposición de contraseñas en el flujo de trabajo.

### Cambiado

- Ejecución eficiente de secuencias guardadas: El sistema optimiza el uso de recursos locales detectando si un flujo permanente se lanza sin modificaciones para procesarlo directamente a través de su identificador en el motor interno.

## [0.9.71] - 2026-06-19

### Añadido

- Bloques visuales de datos y servicios en el editor: El constructor interactivo de flujos ahora incluye módulos específicos para añadir consultas a bases de datos y peticiones de mensajería empresarial, proporcionando formularios dedicados para configurar conexiones, parámetros, aserciones y variables de destino.

### Cambiado

- Conversión optimizada de flujos dinámicos: Al iniciar una secuencia desde la interfaz, el editor traduce de forma transparente la estructura visual (incluyendo ramas anidadas de condiciones y bucles en cualquier nivel de profundidad) en instrucciones legibles para el motor de ejecución.

## [0.9.70] - 2026-06-19

### Añadido

- Simulación de comportamiento humano real (Tiempos de espera): El módulo de rendimiento ahora permite configurar intervalos de espera realistas entre acciones de usuarios virtuales, emulando con precisión el comportamiento humano y evitando ráfagas artificiales que distorsionen los resultados.
- Escalones y rampas de carga personalizadas: Diseña pruebas avanzadas de pico, estrés y resistencia definiendo etapas progresivas (por ejemplo, incrementar usuarios paulatinamente, mantener el tope de carga y de-escalar al final) en una sola corrida automatizada.
- Generación local de alto rendimiento: Las simulaciones de carga pesada ahora pueden distribuirse automáticamente entre todos los núcleos del procesador de tu equipo, multiplicando la capacidad local de generación de tráfico.
- Arquitectura de carga distribuida en red: Se habilitaron los modos de operación Coordinador y Agente, permitiendo enlazar múltiples computadoras en red para alcanzar volúmenes de tráfico masivo distribuidos desde diferentes frentes.
- Evaluación automatizada de niveles de servicio (SLA): Define los objetivos de calidad esperados (tiempos máximos de respuesta, porcentajes de error tolerados o transacciones mínimas). El sistema contrastará los resultados reales e indicará de inmediato si la prueba aprobó o falló los criterios empresariales.
- Análisis detallado de fallos bajo presión: El reporte de rendimiento ahora agrupa y desglosa los errores específicos detectados por cada servicio afectado, facilitando la identificación exacta del cuello de botella bajo escenarios de estrés.
- Flujos de prueba con lógica inteligente: Las secuencias de validación evolucionaron de listas lineales a flujos dinámicos. Ahora es posible incorporar condiciones lógicas avanzadas (ejecutar pasos si se cumple una regla, repetir acciones un número de veces o iterar mientras una condición sea verdadera), incluyendo topes de seguridad contra bucles infinitos.
- Editor visual de flujos lógicos: Se incorporó un constructor interactivo arrastrable y anidable directamente en la interfaz. Permite modelar, ordenar y enlazar bloques de peticiones, condicionales y bucles visualmente sin escribir líneas de código complejas.
- Pasos integrados de bases de datos: Las secuencias de validación ahora pueden intercalar consultas directas a bases de datos corporativas para preparar o certificar datos en caliente, extrayendo valores de forma segura a través de variables del sistema.
- Integración nativa con servicios de mensajería empresarial: Soporte integrado para invocar servicios de comunicación unaria basados en alto rendimiento, descubriendo automáticamente sus métodos disponibles a partir del servidor y estructurando los mensajes de forma visual.

### Cambiado

- Nomenclatura neutral e intuitiva: Se optimizaron los textos, títulos y etiquetas del panel de servicios para utilizar un vocabulario propio del producto, descriptivo y neutral, conservando una compatibilidad clara para importar formatos comunes del mercado.
- Carga modular y tolerante de componentes: Las conexiones avanzadas de bases de datos y mensajería se activan únicamente bajo demanda, asegurando que la falta de un complemento local no afecte en absoluto al arranque ni a las demás funciones de la herramienta.

### Corregido

- Estabilización visual en el inicio de licencias: Se eliminó el parpadeo temporal que mostraba candados o insignias de bloqueo durante los primeros segundos del arranque. La aplicación ahora recuerda de inmediato tu último plan válido, garantizando un inicio de sesión limpio, fluido y libre de alertas confusas.

## [0.9.69] - 2026-06-04

### Añadido

- Evidencias automáticas en pasos de verificación: En los escenarios de prueba donde el paso de validación (Then) consista únicamente en comprobar un estado lógico o un elemento de la interfaz, el sistema ahora tomará de forma automática una captura de pantalla de respaldo y la incrustará en el reporte PDF final para certificar el resultado visual.
- Soporte avanzado para arquitecturas web modernas (Componentes encapsulados): El motor de grabación y el generador de pruebas ahora detectan de forma automática elementos alojados dentro de estructuras web complejas o anidadas (como portales empresariales de última generación o librerías modernas). El sistema es capaz de atravesar múltiples capas de encapsulamiento para construir selectores altamente fiables, permitiendo automatizar botones, campos y menús que antes eran inaccesibles, tanto en flujos step by step como BDD (Behave).
- Interacción visual y evidencias enriquecidas en aplicaciones de escritorio (Legacy): Durante la ejecución de pruebas en software de escritorio (Legacy), la aplicación ahora desplaza el cursor de forma fluida y visible hacia cada control, resaltándolo con un recuadro dinámico para que la interacción sea claramente observable en pantalla en tiempo real. Adicionalmente, captura de forma automática una evidencia enmarcada de cada elemento interactuado junto al estado final de la ventana, adjuntándolas directamente al reporte PDF final. Los tiempos de transición y las pausas entre pasos son completamente personalizables mediante parámetros de configuración del sistema para adaptarse con precisión al ritmo y velocidad de respuesta de cada aplicación.

### Cambiado

- Navegación automatizada más limpia: Se optimizó el comportamiento de Chrome durante las ejecuciones de prueba, desactivando por completo las alertas y ventanas emergentes (popups) nativas del navegador que sugieren guardar o actualizar contraseñas personales, evitando así bloqueos visuales en los flujos de automatización.
- Captura mejorada de campos de credenciales: El motor de grabación web fue ajustado para interpretar de forma correcta las interacciones dentro de campos de contraseña protegidos, asegurando que las acciones de entrada queden registradas fielmente en el flujo de la prueba.
- Mayor estabilidad en la autoreparación por IA: Se refinaron los criterios del motor de captura y del asistente de recuperación avanzada (potenciado por el modelo local de IA). Esta actualización permite construir selectores de interfaz significativamente más estables, minimizando las sugerencias inadecuadas en aplicaciones complejas.

### Corregido

- Registro inteligente de cuadros de texto: Se corrigió la forma en que el motor de captura interpreta cuando un usuario borra o sobrescribe el contenido de un campo de entrada. El sistema ahora descarta los pasos intermedios y procesa únicamente el texto final, previniendo la duplicación innecesaria de acciones en el script Gherkin.
- Integridad total en reportes PDF: Se solucionó un inconveniente en la estructura de los proyectos de prueba que provocaba la omisión ocasional de imágenes de evidencia. El generador ahora garantiza que las capturas de pantalla tomadas se adjunten de manera ordenada y correcta en el reporte de ejecución por cada scenario.

## [0.9.68] - 2026-06-01

### Añadido

- Control de instancia única: La aplicación ahora se ejecuta bajo una única sesión activa y segura en el equipo. Si intentas abrir el software varias veces por accidente, el sistema detectará de forma inteligente el proceso existente y evitará la duplicación de servicios locales para proteger los recursos de tu máquina.
- Gestión inteligente de pestañas de navegación: Se incorporó un sistema de control de sesiones que unifica la interfaz en una sola pestaña principal. Si abres ventanas secundarias para tareas específicas de grabación, estas se cerrarán automáticamente al concluir el flujo, manteniendo tu área de trabajo limpia y asegurando la sincronización de tus tareas en progreso.

### Cambiado

- Inicio optimizado de la aplicación: Lanzar el acceso directo de ELIA en Windows por segunda vez ahora te redirigirá automáticamente a la interfaz que ya tengas abierta en lugar de abrir ventanas duplicadas. Además, las sesiones de grabación web se iniciarán siempre de manera completamente limpia, evitando la restauración involuntaria de páginas web de sesiones anteriores del navegador.
- Entorno de navegación dedicado y aislado: A partir de ahora, la interfaz de la aplicación se abre de forma automática utilizando un perfil de navegación completamente independiente y exclusivo para ELIA. Esto garantiza que tus sesiones de automatización y trabajo queden totalmente separadas de tu navegador personal, protegiendo tu historial, contraseñas y datos habituales.
- Inicio limpio y libre de distracciones: Cada vez que arranques la aplicación, la ventana mostrará única y exclusivamente el panel de control de ELIA. Se eliminó por completo la restauración automática de pestañas antiguas, páginas ajenas o sesiones previas de tu navegador principal, asegurando un espacio de trabajo despejado desde el primer segundo.
- Rediseño estético del Tema Oscuro: Se mejoró visualmente toda la interfaz para ofrecer una experiencia mucho más integrada y cómoda para la vista. Las casillas de verificación, cuadros de texto, barras de desplazamiento y campos de filtrado de pruebas BDD ahora adaptan sus colores nativos y contornos al modo oscuro de forma homogénea.

### Corregido

- Estabilidad en la consola de ejecución: Se solucionó un problema de bloqueo en entornos Windows al procesar ejecuciones largas de pruebas BDD. Ahora, incluso si un paso de automatización falla durante la corrida, la consola concluirá correctamente su ciclo de lectura y generará de forma fiable el reporte de evidencias en PDF con el estado del error.
- Control de apagado confiable: Se eliminó el sistema automático de cierre por inactividad en segundo plano. La aplicación ya no se desconectará de forma inesperada si la dejas en espera; ahora, solo detendrá sus servicios locales cuando cierres explícitamente la pestaña principal de la interfaz.
- Corrección en la persistencia de tareas: Cerrar pestañas secundarias o de descarte ya no provocará el apagado accidental del software. Asimismo, aquellas tareas que hayan sido canceladas o interrumpidas en segundo plano dejarán de mostrar el indicador visual indefinido de «Cargando...», liberando la pantalla de inmediato.
- Fluidez en la navegación de proyectos: Al finalizar con éxito una conversión automatizada, el panel de inicio refrescará al instante tu catálogo de proyectos disponibles. Además, ahora puedes recargar la interfaz de forma segura (presionando F5) sin temor a perder tu sesión activa ni interrumpir la comunicación con la aplicación.
- Persistencia visual: Se garantizó que tu preferencia de tema (claro u oscuro) se mantenga guardada de forma correcta y se aplique de manera inmediata desde el primer instante en que vuelves a arrancar la aplicación.
- Reporte PDF de evidencias Behave: El emparejamiento de capturas con cada paso Gherkin usa la misma numeración secuencial que la generación de imágenes (`02_when`, `03_and`, etc.), de modo que todas las evidencias del escenario se incluyen en el PDF y no solo la del Given.
- Paso Then en conversión web: Al ejecutar el Then de validación se captura el estado final de la pantalla y se adjunta al PDF como el resto de pasos.

## [0.9.67] - 2026-05-31

### Añadido

- Sistema de licencias de alta seguridad empresarial: Se implementó una nueva arquitectura de validación de firmas asimétricas de grado gubernamental para la activación de la aplicación. Esto garantiza que la autenticación del software sea completamente infalsificable y se procese localmente de forma ultra-rápida en el equipo.
- Infraestructura para renovación transparente de accesos: Capacidad nativa para gestionar y actualizar múltiples claves de verificación integradas en la aplicación, permitiendo migraciones de seguridad y renovaciones sin interrumpir el trabajo del usuario.
- Entorno blindado para la emisión de accesos: Se aislaron las herramientas de generación y control de licencias corporativas en un entorno externo protegido por autenticación multifactor, añadiendo una auditoría local estricta sobre cada activación emitida.

### Cambiado

- Compatibilidad con accesos anteriores: El sistema mantiene soporte nativo de retrocompatibilidad para validar de forma transparente las claves emitidas bajo formatos previos, asegurando una transición fluida para los usuarios actuales.

### Seguridad

- Blindaje del código de la aplicación: Se removieron de forma absoluta todas las semillas y secretos de generación interna del ejecutable de ELIA. Al no existir algoritmos de creación dentro del cliente, se elimina cualquier vector de vulnerabilidad o intento de alteración de software en el equipo del usuario.
- Autenticación obligatoria de seguridad: El proceso de firmas comerciales ahora requiere validación temporal y controles de identidad obligatorios para blindar el canal de distribución oficial.

## [0.9.66] - 2026-05-30

### Añadido

- Modelos de suscripción estructurados (Basic, Professional y Enterprise): Se introdujo una distribución comercial por niveles que organiza de forma clara las características de la aplicación (automatización web/móvil, pruebas de API, IA de documentos, reportes de carga masiva y memorias compartidas de equipo) según las necesidades de cada organización.
- Licencia Beta Global de acceso inmediato: Se integró una clave de acceso general simplificada y sin restricciones de hardware, diseñada específicamente para facilitar la instalación plug-and-play a los participantes del programa de pruebas Beta.
- Protección del ciclo de vida de la fase Beta: Nueva configuración automatizada para la campaña de pruebas con una fecha de caducidad definitiva, protegida por un sistema inteligente de validación horaria por red y un escudo anti-retroceso de tiempo para evitar alteraciones.
- Indicadores de características avanzadas: Se incorporaron insignias descriptivas y pantallas informativas amigables en la interfaz para identificar de forma clara las funciones exclusivas de los planes Professional y Enterprise dentro de los módulos de API y automatización de flujos.

### Cambiado

- Ajuste en la asignación de funciones por nivel: El acceso a los componentes de la interfaz ahora se valida en tiempo real según el nivel de suscripción activo. La conversión inteligente de documentos mediante IA local (Doc-to-BDD) pasa a formar parte de las herramientas avanzadas a partir del plan Professional.
- Protección de vigencia inalterable: La fecha límite del periodo de pruebas se grabó de forma estricta en el núcleo de la aplicación, previniendo modificaciones o extensiones externas involuntarias para asegurar un cierre de campaña limpio.

### Corregido

- Optimización del motor de validación: Se corrigieron flujos de procesamiento internos en el módulo de licencias locales, acelerando notablemente los tiempos de arranque e inicio de la aplicación.
- Mayor estabilidad en la captura de escritorio: Se solucionó un comportamiento intermitente que provocaba la pérdida ocasional de eventos de teclado durante las sesiones de grabación en aplicaciones de escritorio clásicas (Legacy).

## [0.9.65] - 2026-05-30

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

## [0.9.60] - 2026-05-31

### Añadido

- Diseño avanzado para pruebas de servicios: Nueva interfaz con vista dividida (tipo Maestro-Detalle) para la gestión de API. Ahora dispones de un panel lateral dedicado para explorar tus escenarios, importaciones y capturas, junto con un espacio de trabajo central organizado en pestañas para alternar rápidamente entre la configuración del Entorno y los detalles de la Petición.

### Cambiado

- Organización visual optimizada: Se reestructuró la lógica interna de los paneles de API para ofrecer una navegación mucho más limpia, manteniendo el acceso directo a las pruebas de carga sin alterar tus flujos de trabajo existentes.

## [0.9.55] - 2026-05-30

### Añadido

- Explorador de archivos en árbol: En el espacio de ejecución, la lista plana de archivos se reemplazó por un árbol de directorios colapsable y organizado, lo que facilita navegar por carpetas en proyectos grandes de automatización.

### Cambiado

- Diseño de cabecera unificado: Se restauró la distribución original de la barra superior, devolviendo los logotipos principales del producto a la esquina izquierda para una identidad visual más limpia, manteniendo el indicador de asistencia de IA accesible.
- Interfaces más limpias y asistidas: Se eliminaron párrafos e instrucciones explicativas repetitivas en las secciones de automatización de escritorio (Legacy) y pruebas BDD, sustituyéndolas por discretos cuadros de ayuda flotantes (tooltips) que aparecen al pasar el cursor sobre las etiquetas de los campos.

## [0.9.51] - 2026-05-30

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
