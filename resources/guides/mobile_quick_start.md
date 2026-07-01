Guía rápida — Automatización móvil (Android)

En ELIA, los proyectos Behave de móvil se crean al convertir una grabación. No uses plantillas web: el flujo natural es grabar tu app y generar el escenario.

1. Revisa el entorno
   - Abre el checklist «Entorno Android» en la pantalla de grabación.
   - Confirma adb, SDK, Appium y un dispositivo o emulador conectado.
   - Si falta algo, usa Configuración → Entorno local o el asistente AVD (plan Architect).

2. Configura la sesión
   - Elige dispositivo físico o emulador.
   - Indica package y activity de la app, o instala un APK si aplica.
   - Inicia Appium desde la propia pantalla si aún no está en marcha.

3. Graba el flujo
   - Pulsa Grabar, interactúa con la app y detén la grabación.
   - Asigna un nombre de proyecto al convertir (se creará en behave/mobile/).

4. Convierte a Behave
   - Ejecuta la conversión mobile_to_behave desde la cola de trabajos.
   - Revisa el .feature y los steps generados en el proyecto.

5. Ejecuta y evidencias
   - En la sección «Ejecutar Behave», selecciona el proyecto y el .feature.
   - Activa evidencia PDF si necesitas informe con capturas.

Problemas frecuentes
   - Appium no responde: reinicia el servidor desde la UI o comprueba el puerto 4723.
   - Dispositivo no listado: adb devices, reinicia el emulador o revisa drivers USB.
   - Package incorrecto: usa «Detectar app en primer plano» con la app abierta en el dispositivo.
