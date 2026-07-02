Guía rápida — Suites y carga (Pruebas API)

La pestaña **Suites y carga** agrupa datos CSV, ejecución encadenada de escenarios y pruebas de rendimiento con Locust. Sigue este orden la primera vez.

1. Prepara escenarios en Cliente API
   - En la pestaña **Cliente API**, envía peticiones y guárdalas como escenarios.
   - Opcional: importa una colección Postman u OpenAPI.

2. Datos CSV (opcional)
   - Si necesitas variaciones (usuarios, IDs, etc.), importa un `.csv` o `.xlsx` en **Datos CSV**.
   - Excel se convierte a CSV en `resources/data/` del proyecto.

3. Suite funcional
   - Marca los escenarios que quieres encadenar.
   - Elige archivo CSV si la suite es data-driven.
   - Ejecuta la suite y revisa el progreso en la consola.

4. Prueba de carga
   - Selecciona perfil (carga, estrés, spike, etc.) y usuarios/duración.
   - Con perfil **Volumen**, vincula un CSV para rotar filas entre usuarios virtuales.
   - Revisa métricas en vivo (RPS, latencias, SLA).

Consejos
   - Empieza con pocos escenarios y un perfil **Carga sostenida** antes de estrés o spike.
   - Usa **Abrir carpeta de datos** para revisar CSV en el explorador del sistema.
   - Los escenarios comparten variables de entorno definidas en Cliente API.
