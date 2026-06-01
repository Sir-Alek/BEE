================================================================================
  ELIA — Evolving Learning & Intelligent Automation
================================================================================

ELIA es una plataforma avanzada de ingeniería de calidad que transforma el ciclo de 
vida de las pruebas de software. Diseñada estratégicamente para romper la barrera entre 
el QA Manual y la Automatización, ELIA empodera a los analistas funcionales para capturar 
flujos de negocio complejos, mientras entrega a los Ingenieros de Automatización un código
base estructurado y listo para escalar. Al automatizar la captura de selectores (DOM) y la 
creación de la arquitectura base, ELIA elimina hasta un 80% del trabajo técnico repetitivo.

CAPACIDADES PRINCIPALES
A través de su motor heurístico y su Inteligencia Artificial, ELIA traduce las interacciones 
web del usuario en especificaciones vivas: desde proyectos robustos en Behave BDD (Python) de 
forma nativa, hasta documentación paso a paso con evidencia visual. Sus módulos de Inteligencia 
de Requerimientos permiten además ingerir historias de usuario en texto plano (Word/Excel) para 
generar escenarios Gherkin perfectamente alineados con el estilo de tu equipo.

APRENDIZAJE EVOLUTIVO
Lo que distingue a ELIA es su capacidad de adaptación.
El sistema aprende de la experiencia acumulada: al recibir feedback del usuario sobre las
conversiones generadas, el modelo evoluciona, afinando su precisión y ajustándose al estilo 
de codificación único de tu organización. ELIA no solo automatiza, sino que mejora su desempeño
con cada iteración.

PRIVACIDAD POR DISEÑO (ZERO-TRUST)
Todo el ecosistema de ELIA opera bajo un enfoque de privacidad estricta. 
El procesamiento principal, la conversión y el almacenamiento ocurren 100% 
en tu equipo: tus flujos de negocio, credenciales y documentos nunca se envían 
a nubes externas por defecto.
Incluso su cerebro de Inteligencia Artificial (impulsado por modelos compatibles
como la familia Gemma) se ejecuta de forma local, garantizando la seguridad de
tu infraestructura corporativa sin sacrificar innovación tecnológica.

--------------------------------------------------------------------------------
  REQUISITOS (Windows)
--------------------------------------------------------------------------------

  • Windows 10/11 de 64 bits.
  • Google Chrome instalado (obligatorio para grabación web).
    Microsoft Edge no sustituye a Chrome en la grabación.
  • Conexión a red/Internet: Necesaria para acceder a las páginas web que deseas grabar
   y para las integraciones (Jira, ValueEdge). Sin embargo, todo el procesamiento, 
   incluyendo la inteligencia y conversión de ELIA se realiza de forma estrictamente local.
  • Para inteligencia local (IA): modelo de lenguaje compatible incluido (familia Gemma)
   o colocado en la carpeta de recursos del producto, y recomendable ≥ 8 GB de RAM total
   con ≥ 4 GB libres (modo Automático). Sin IA, las conversiones usan reglas heurísticas rápidas.

  Si Chrome no está en la ruta habitual, tu administrador puede definir antes de
  abrir ELIA la variable de entorno:
    ELIA_CHROME_PATH=C:\ruta\completa\chrome.exe

--------------------------------------------------------------------------------
  REQUISITOS DE CONECTIVIDAD Y SEGURIDAD
--------------------------------------------------------------------------------

  ELIA está diseñado bajo una arquitectura Local-First para proteger la privacidad 
  de tus datos. Sin embargo, para explotar el 100% de su valor, requiere acceso 
  a internet por las siguientes razones técnicas:
  
  1. Integración ALM: Conectividad obligatoria para la carga/descarga de datos 
     en plataformas como Jira y Value Edge.
  2. Pruebas de API y Grabación: Necesaria para interactuar con entornos de 
     staging, microservicios externos y ejecución de pruebas distribuidas.
  3. Validación de Entorno: Al arrancar, el backend de ELIA sincroniza de forma 
     segura con servidores de tiempo para validar la integridad del periodo de 
     la beta. Alterar de forma manual el reloj del sistema operativo o bloquear 
     completamente las salidas HTTP del backend provocará el bloqueo preventivo 
     de la aplicación por seguridad.

--------------------------------------------------------------------------------
  INICIO RÁPIDO
--------------------------------------------------------------------------------

  1. Instala ELIA con el asistente (ELIA_Setup) o ejecuta ELIA.exe según indique
     tu organización.
  2. Abre ELIA desde el acceso directo. Se abrirá el navegador en la dirección
     local de la aplicación (por ejemplo http://127.0.0.1 y un puerto).
  3. Mantén abierta la pestaña de INICIO: desde ahí lanzas cada operación; el
     resto de ventanas (grabación, avisos, resultados) se abren en pestañas nuevas.
  4. Usa el icono de engranaje (Configuración) para licencia, inteligencia, temas
     y conectores externos.

  Al cerrar la pestaña principal en tu navegador, el motor local de ELIA se detendrá
  automáticamente para liberar recursos.

--------------------------------------------------------------------------------
  PROGRAMA DE BETA PÚBLICA (JUNIO 2026)
--------------------------------------------------------------------------------

  Esta distribución de ELIA pertenece a una fase de Beta Pública exclusiva. 
  
  • Duración de la Beta: 30 días, activa desde el 1 de junio de 2026 hasta su 
    fecha límite automática el 30 de junio de 2026 a las 23:59:59 UTC.
  • Acceso Completo: Todas las capacidades premium (Automatización Web/Mobile, 
    generación BDD e Inteligencia Artificial) están desbloqueadas de fábrica.
  • Sin Claves de Activación: El software es "Plug-and-Play". No necesitas 
    registrarte ni solicitar licencias para comenzar a usarlo.
  • Finalización del Periodo: Al cumplirse la fecha límite, el sistema se 
    bloqueará automáticamente. Para conservar tus proyectos y continuar usando 
    ELIA, se requerirá una suscripción comercial activa.

--------------------------------------------------------------------------------
  PANTALLA DE INICIO — TRES ÁREAS DE TRABAJO
--------------------------------------------------------------------------------

  A) AUTOMATIZACIÓN UI (WEB Y MÓVIL)
     • Grabar interacciones: indica la URL o configuración del dispositivo, pulsa 
       «Grabar Interacciones» e interactúa en el navegador o emulador nativo. 
       Al cerrar la ventana se guarda la grabación del flujo de negocio.
     • Convertir a Behave: genera features y steps en formato BDD (Behave/Python)
       a partir de una o varias grabaciones del proyecto.
     • Convertir a step by step: genera documentación paso a paso con capturas de
       evidencia visual según la grabación elegida.
     • Editor y Runner Embebido: visualiza, realiza ediciones rápidas a tus scripts 
       y ejecuta las pruebas BDD de Behave directamente desde la interfaz de ELIA 
       mediante un entorno de ejecución integrado, sin depender de IDEs externos.
     • Exportar y Publicar: sube de forma directa los archivos .feature y las 
       evidencias generadas hacia repositorios Git o las plataformas ALM conectadas.

     Según tu distribución o licencia activa:
     • Automatización Móvil Nativa (Módulo Appium integrado para Android).
     • Grabación y conversión Legacy (módulo adicional).

  B) INTELIGENCIA DE REQUERIMIENTOS Y CONECTORES
     • Ingesta Local: carga documentos locales Word (.docx) o Excel (.xlsx) con 
       historias de usuario y criterios de aceptación tradicionales.
     • Extracción ALM Remota: se conecta vía API a Jira (Vanilla/Xray), Azure 
       DevOps o OpenText Value Edge para descargar requerimientos vivos del proyecto.
     • Vinculación inteligente: opcionalmente vincula la conversión a un escenario
       BDD ya existente en el proyecto (a partir de grabaciones previas).
     • «Procesar y Convertir a BDD»: genera escenarios Gherkin estructurados en la
       carpeta del proyecto, usando IA local cuando está activa o reglas rápidas.
     • Sincronización Bi-direccional: publica y actualiza los scripts Gherkin de 
       regreso en el ticket o repositorio de origen directamente desde la app.

  C) PRUEBAS DE API Y RENDIMIENTO
     • Panel Maestro-Detalle: interfaz dividida que permite explorar colecciones, 
       organizar ambientes y saltar entre endpoints en segundos de forma lateral.
     • Importar especificaciones: ingesta rápida de colecciones de Postman o 
       documentos OpenAPI para poblar de inmediato el árbol de pruebas de servicios.
     • Editor y Aserciones: configura cabeceras, parámetros, métodos HTTP y payloads 
       con reglas de validación automáticas sobre el JSON o XML de respuesta.
     • Ejecución de Carga (Locust): motor integrado para lanzar simulaciones de 
       rendimiento y estrés sobre las APIs configuradas, midiendo tiempos de respuesta.

--------------------------------------------------------------------------------
  INTELIGENCIA LOCAL
--------------------------------------------------------------------------------

  En Configuración → pestaña «Inteligencia» puedes elegir:

    • Automático (recomendado): usa IA solo si el modelo está disponible, el motor
      local responde y hay RAM suficiente; si no, convierte en modo rápido.
    • Siempre activada: intenta IA en cada conversión (puede ir lento si falta RAM).
    • Desactivada: solo conversiones heurísticas, sin modelo generativo.

  La comprobación de RAM no es continua durante un lote largo: se evalúa al iniciar
  cada trabajo y al refrescar el estado en Configuración.
  ELIA puede recordar correcciones que hagas en BDD (memoria local) para afinar
  futuras sugerencias de redacción.

--------------------------------------------------------------------------------
  CONECTORES Y PUBLICADORES (EXTRACCIÓN Y SUBIDA)
--------------------------------------------------------------------------------

  ELIA es un ecosistema bi-direccional. No solo extrae requerimientos, sino que publica los resultados:

  • Conectores ALM Soportados:
    - Jira (Vanilla Cloud / On-Premise) y Jira Xray (Gestión de Pruebas).
    - OpenText Value Edge (Entornos corporativos de calidad).
    - Azure DevOps (Sincronización nativa de Work Items).
    - Git (Integración directa con repositorios GitHub/GitLab mediante tokens).

  • Capacidades del Flujo Digital:
    - Extracción (Download): Ingesta directa de historias de usuario, épicas 
      y criterios de aceptación para alimentar al motor heurístico/IA.
    - Publicación (Upload): Capacidad nativa de subir y exportar los archivos 
      Gherkin (.feature) resultantes y las evidencias de prueba directamente a 
      las plataformas de origen o ramas de Git desde el panel de la aplicación.

--------------------------------------------------------------------------------
  DÓNDE SE GUARDAN TUS ARCHIVOS
--------------------------------------------------------------------------------

  Por defecto, proyectos, grabaciones y salidas bajo:
    Documentos\ELIA\
  (y las configuraciones de la aplicación, como preferencias de IA y perfiles de conexión,
  se gestionan de forma segura en el perfil local de tu usuario en Windows).
  Tu administrador puede redirigir la raíz con la variable ELIA_USER_DATA.

--------------------------------------------------------------------------------
  CONFIGURACIÓN (RESUMEN DE PESTAÑAS)
--------------------------------------------------------------------------------

  El diálogo global de configuración permite moldear el comportamiento del backend 
  de FastAPI y la UI a través de 5 pestañas esenciales:

  • General — Control visual de la interfaz (conmutación de tema claro/oscuro) 
    y preferencias de logs y alertas de la plataforma.
  • Inteligencia — Configuración del motor de IA local (Gemma). Permite validar 
    la capacidad de hardware (RAM libre), comprobar la integridad del archivo 
    GGUF y alternar los modos de asistencia automatizada.
  • Conectores — Panel centralizado para dar de alta y probar credenciales. 
    Permite configurar URLs, credenciales y tokens de acceso para Jira, Xray, 
    Value Edge, Azure DevOps y Git, con validación de conexión en tiempo real.
  • Licencia — Estado del periodo de pruebas de la Beta Pública. Monitorea de 
    forma autónoma el tiempo restante de tus 30 días de uso libre sin requerir 
    intervención o activación manual.
  • Acerca de — Resumen de metadatos de ELIA: versión del producto (0.9.67), 
    créditos del desarrollador, enlaces al canal oficial de soporte y acceso al 
    formulario exclusivo para reportar feedback de la beta.

--------------------------------------------------------------------------------
  SOPORTE, FEEDBACK Y DOCUMENTACIÓN TÉCNICA
--------------------------------------------------------------------------------

  Tu opinión es lo más valioso para definir el futuro de la herramienta. Si 
  encuentras un bug o tienes sugerencias de mejora:
  
  • Formulario de Feedback Beta: https://forms.gle/Ep4AzkPToW8A2Zd99
  • Correo de Contacto: elia.qa.software+contacto@gmail.com
  • Versión del Producto: 0.9.67 (Canal: Beta Pública)
  • Desarrollador: Alejandro Ramírez </Sir_Alek>

================================================================================
