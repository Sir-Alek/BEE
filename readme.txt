================================================================================
  ELIA — Evolving Learning & Intelligent Automation
================================================================================

ELIA es una suite local de ingeniería de calidad. Graba interacciones en
aplicaciones web, convierte esas grabaciones en pruebas automatizadas (Behave
BDD o guías step-by-step con evidencias) y, con módulos adicionales, procesa
historias de usuario en Word o Excel para generar escenarios Gherkin alineados
con el estilo de tu equipo.

Todo el procesamiento principal ocurre en tu equipo: no envía tus grabaciones ni
documentos a la nube por defecto. La inteligencia opcional (modelo Gemma) también
se ejecuta de forma local cuando está habilitada y el equipo cumple los requisitos
de memoria.

--------------------------------------------------------------------------------
  REQUISITOS (Windows)
--------------------------------------------------------------------------------

  • Windows 10/11 de 64 bits.
  • Google Chrome instalado (obligatorio para grabación web).
    Microsoft Edge no sustituye a Chrome en la grabación.
  • Conexión a Internet solo si usas integraciones (Jira, Value Edge) o descargas
    opcionales; el núcleo de grabación y conversión funciona sin red.
  • Para inteligencia local (IA): modelo Gemma incluido o colocado en la carpeta
    de recursos del producto, y recomendable ≥ 8 GB de RAM total con ≥ 4 GB libres
    (modo Automático). Sin IA, las conversiones usan reglas heurísticas rápidas.

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

  Al cerrar la pestaña de inicio, ELIA puede finalizar el proceso en segundo plano.

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
  INTELIGENCIA LOCAL (GEMMA)
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
  CONECTORES (JIRA Y VALUE EDGE)
--------------------------------------------------------------------------------

  En Configuración → «Conectores» puedes guardar perfiles con credenciales para:

    • Jira — extracción y trabajo con issues.
    • Value Edge — integración con espacios y flujos configurados.

  Desde la pantalla de inicio también hay accesos rápidos para probar conexión y
  lanzar flujos asociados (por ejemplo «Conectar a Jira»), según lo habilitado en
  tu instalación.

  Las credenciales se guardan en tu perfil de usuario de Windows (datos locales de
  ELIA), no en el instalador. Consulta a tu administrador la política de secretos.

--------------------------------------------------------------------------------
  LICENCIA
--------------------------------------------------------------------------------

  • Modo demostración: período limitado desde el primer uso.
  • Activación: pestaña «Licencia» en Configuración, o clave proporcionada por tu
    organización (también puede configurarse por variable de entorno antes del
    arranque, según política interna).
  • Módulos extra (móvil, legacy, documentos avanzados) dependen del tipo de clave.

--------------------------------------------------------------------------------
  DÓNDE SE GUARDAN TUS ARCHIVOS
--------------------------------------------------------------------------------

  Por defecto, proyectos, grabaciones y salidas bajo:

    Documentos\ELIA\

  (y datos de aplicación — licencia, preferencias de IA, conectores — en la carpeta
  de datos de usuario de ELIA en Windows, normalmente bajo %LOCALAPPDATA%\ELIA\).

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

  Para despliegue, compilación e integraciones avanzadas, el equipo de desarrollo
  dispone de readme_dev.md en el repositorio del producto (no incluido en todas
  las entregas al usuario final).

  Versión mostrada en la aplicación: pestaña Configuración → Acerca de.

  Desarrollador: Alejandro Ramírez </Sir_Alek>

================================================================================
