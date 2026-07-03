# ELIA Visual Language v1

## Principio

**Misma ADN, distinta intensidad.** Splash = atmósfera. UI = herramienta estable (90%) + feedback con movimiento (10%).

## Taxonomía de carga

| Nivel | Uso | Componente |
|-------|-----|------------|
| Ceremonial | Boot de app | `EliaSplashScreen` |
| Operativa | Fetch, validaciones | `.elia-loading-row` + `.elia-spinner` |
| Estado | Grabar, jobs, Locust | `.elia-state-running` |

## Primitivos

- `.elia-panel` — tarjetas y secciones
- `.elia-btn` / `--ghost` / `--primary` / `--tab` — botones
- `.elia-input` — campos con glow al foco
- `.elia-chrome` — header consola
- `.elia-mono` — URLs, paths, logs
- `.elia-spinner` — spinner inline 14px
- `.elia-loading-row` — fila estado + texto

## Temas

- Oscuro: identidad plena (`#030712`, acento `#00d2ff`)
- Claro: misma estructura, glow reducido (`#f8fafc`, acento `#0891b2`)
- Splash respeta `data-elia-theme`

## Neón semántico

- Cyan: ELIA trabaja / running
- Verde: OK
- Rojo: error
- Magenta: reservado acciones especiales

## Reglas

- No anillos HUD en UI de trabajo
- Degradado solo en hover/activo de botones primarios
- `prefers-reduced-motion`: crossfade y spinner pulsante
- Modo HUD (`data-elia-hud="1"`): amplifica bordes, opt-in
