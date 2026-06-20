# Guía de funciones para Page Objects (ELIA)

Este documento explica cómo usar las funciones de automatización disponibles en tus proyectos Behave.
**No necesitas editar la implementación interna** salvo casos avanzados: personaliza `pages/*_page.py` y los steps.

> Implementación Python (avanzado): `utils/button_functions.py` — visible en el runner con «Mostrar código avanzado».

## Importación habitual

```python
from utils.button_functions import ui_interact, ui_navigate, take_global_evidence
# o, para muchos métodos:
from utils.button_functions import *
```

En los **Page Objects** (`pages/mi_flujo_page.py`) define métodos que llamen a estas funciones con `self.driver`.

---

## Web (Selenium / Chrome)

### `ui_navigate(driver, url, nombre_pagina=..., usar_create_screenshot=False)`

Abre una URL, espera overlays comunes y opcionalmente captura evidencia.

```python
def abrir_login(self):
    ui_navigate(self.driver, self.urls["login"], "Pantalla_Login")
```

### `ui_interact(driver, xPath_elemento, accion, nombre_elemento=..., valor=None, ...)`

Interacción principal con la UI. Acciones (`accion`):

| Valor | Uso |
|-------|-----|
| `click` | Clic en elemento |
| `insertTxt` | Escribir texto (borra contenido previo) |
| `insertTxtTab` | Escribir y pulsar Tab |
| `getValue` | Leer valor del campo |
| `highlight` | Resaltar sin clic |
| `assertNotVisible` | Comprobar que no es visible |

```python
def click_continuar(self):
    ui_interact(
        self.driver,
        self.elements["btn_continuar"],
        "click",
        nombre_elemento="Continuar",
    )

def escribir_usuario(self, texto):
    ui_interact(
        self.driver,
        self.elements["input_user"],
        "insertTxt",
        nombre_elemento="Usuario",
        valor=texto,
    )
```

Parámetros útiles: `iframe_xpath` (elementos en iframe), `timeout`, `usar_create_screenshot=True` para evidencia.

### `ui_validate_text`, `ui_validate_download`, `ui_validate_excel_content`

Validaciones post-acción (texto en pantalla, ficheros descargados, Excel). Úsalas en métodos `Then` del page object.

### `take_global_evidence` / `create_screenshot`

Capturas para el reporte PDF cuando `GENERATE_EVIDENCE=true`.

### `hide_material_tooltips`, `ui_cleanup_state`

Limpieza de tooltips Material y estado UI antes/después de pasos delicados.

---

## Escritorio Legacy (Windows)

### `legacy_click(x, y, nombre_elemento=..., step=..., usar_create_screenshot=False)`

Clic por coordenadas con movimiento visible y evidencia opcional.

### `legacy_capture_screen(step, nombre_elemento=..., usar_create_screenshot=False)`

Captura de pantalla completa del escritorio.

### `activate_window_by_title_contains(titulo_parcial, ...)`

Activa una ventana cuyo título contiene el texto indicado.

---

## Evidencias globales

### `set_global_evidence_config(take=False, dir_name="", func=None)`

Configura si las funciones deben tomar capturas en el hilo actual (usado por el entorno Behave).

---

## Buenas prácticas

1. **Selectores** en `resources/data/*.json` (`elements`, `urls`) — no hardcodear XPath largos en cada método.
2. **Un método = una acción de negocio** en el page object; los steps Gherkin llaman `context.page.metodo()`.
3. **Añadir funciones nuevas**: preferible un método en el page object que componga `ui_interact`; solo extiende `button_functions.py` si la lógica es reutilizable en muchos proyectos.
4. Tras guardar cambios en el runner, pulsa **Ejecutar Behave** con el filtro de feature adecuado.

---

## Autocompletado en el editor ELIA

Al escribir en `*_steps.py` o `*_page.py`, el editor sugiere:

- Pasos Gherkin ya definidos en el proyecto
- Métodos del page object (`context.page.…`)
- Nombres de funciones al importar desde `button_functions`

Usa **Ctrl+Espacio** si no aparecen sugerencias automáticamente.
