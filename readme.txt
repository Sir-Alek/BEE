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
  PANTALLA DE INICIO — DOS ÁREAS DE TRABAJO
--------------------------------------------------------------------------------

  A) AUTOMATIZACIÓN UI
     • Grabar interacciones: indica la URL, pulsa «Grabar Interacciones» e interactúa
       en el navegador que se abre. Al cerrar ese navegador se guarda la grabación.
     • Convertir a Behave: genera features y steps en formato BDD (Behave/Python)
       a partir de una o varias grabaciones del proyecto.
     • Convertir a step by step: genera documentación paso a paso con capturas de
       evidencia según la grabación elegida.

     Según tu licencia pueden aparecer también:
     • Grabación y conversión Móvil (módulo adicional).
     • Grabación y conversión Legacy (módulo adicional).

  B) INTELIGENCIA DE REQUERIMIENTOS
     • Carga documentos Word (.docx) o Excel (.xlsx) con historias de usuario.
     • Opcionalmente vincula la conversión a un escenario BDD ya existente en el
       proyecto (a partir de grabaciones previas).
     • «Procesar y Convertir a BDD» genera escenarios Gherkin en la carpeta del
       proyecto, usando IA local cuando está activa o reglas rápidas en modo sin IA.

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
  CONECTORES (JIRA Y VALUEDGE)
--------------------------------------------------------------------------------

  En Configuración → «Conectores» puedes guardar perfiles con credenciales para:

    • Jira — extracción y trabajo con issues.
    • ValueEdge — integración con espacios y flujos configurados.

  Desde la pantalla de inicio también hay accesos rápidos para probar conexión y
  lanzar flujos asociados (por ejemplo «Conectar a Jira»), según lo habilitado en
  tu instalación.

  Las credenciales se guardan en tu perfil de usuario de Windows (datos locales de
  ELIA), no en el instalador. Consulta a tu administrador la política de secretos.

--------------------------------------------------------------------------------
  LICENCIA
--------------------------------------------------------------------------------

  • Activación obligatoria desde el primer uso: sin clave válida no se pueden ejecutar
    tareas de automatización ni conversión con IA.
  • Introduce la clave en Configuración → Licencia (muestra la huella de tu equipo para
    soporte) o según indique tu organización (variable de entorno, etc.).
  • Módulos extra (móvil, legacy, documentos avanzados) dependen del tipo de clave.

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

  • General — tema claro/oscuro y preferencias de interfaz.
  • Inteligencia — modo de IA (automático / siempre / desactivada) y estado del modelo.
  • Conectores — perfiles Jira y Value Edge.
  • Licencia — activación y estado.
  • Acerca de — versión del producto, desarrollador y texto de licencia.

--------------------------------------------------------------------------------
  ESTE ARCHIVO EN LA INSTALACIÓN
--------------------------------------------------------------------------------

  Si instalaste con ELIA_Setup, readme.txt se copia en la carpeta de instalación
  (junto a ELIA.exe) para consulta offline. Una copia puede existir también dentro
  de la carpeta interna del programa (_internal).

--------------------------------------------------------------------------------
  SOPORTE Y DOCUMENTACIÓN TÉCNICA
--------------------------------------------------------------------------------

  Versión mostrada en la aplicación: pestaña Configuración → Acerca de.
  Desarrollador: Alejandro Ramírez </Sir_Alek>

================================================================================
