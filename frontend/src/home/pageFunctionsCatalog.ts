/** Catálogo de funciones públicas de utils/button_functions (autocompletado + hover). */
export type PageFunctionEntry = {
  name: string;
  platforms: ("web" | "legacy" | "all")[];
  signature: string;
  summary: string;
  example?: string;
};

export const PAGE_FUNCTIONS_CATALOG: PageFunctionEntry[] = [
  {
    name: "ui_navigate",
    platforms: ["web"],
    signature: "ui_navigate(driver, url, nombre_pagina=..., usar_create_screenshot=False)",
    summary: "Navega a una URL y espera overlays comunes.",
    example: 'ui_navigate(self.driver, self.urls["home"], "Inicio")',
  },
  {
    name: "ui_interact",
    platforms: ["web"],
    signature:
      "ui_interact(driver, xPath_elemento, accion, nombre_elemento=..., valor=None, iframe_xpath=None, timeout=60, ...)",
    summary: "Clic, texto, lectura o aserción sobre un elemento (accion: click | insertTxt | insertTxtTab | getValue | highlight | assertNotVisible).",
    example: 'ui_interact(self.driver, self.elements["btn_ok"], "click", nombre_elemento="OK")',
  },
  {
    name: "ui_validate_text",
    platforms: ["web"],
    signature: "ui_validate_text(driver, xPath_elemento, texto_esperado, ...)",
    summary: "Comprueba que un elemento contiene el texto esperado.",
  },
  {
    name: "ui_validate_download",
    platforms: ["web"],
    signature: "ui_validate_download(nombre_archivo, timeout=..., ...)",
    summary: "Valida que un fichero apareció en outputs/downloads.",
  },
  {
    name: "ui_validate_excel_content",
    platforms: ["web"],
    signature: "ui_validate_excel_content(ruta, hoja, celda, valor_esperado, ...)",
    summary: "Valida contenido de celda Excel descargado.",
  },
  {
    name: "take_global_evidence",
    platforms: ["all"],
    signature: "take_global_evidence(driver, default_step, nombre_elemento, usar_create_screenshot, screenshot_step=None)",
    summary: "Captura evidencia global si la generación de evidencias está activa.",
  },
  {
    name: "create_screenshot",
    platforms: ["all"],
    signature: "create_screenshot(step, label, dir_name=..., web_driver=...)",
    summary: "Genera captura asociada a un paso del escenario.",
  },
  {
    name: "hide_material_tooltips",
    platforms: ["web"],
    signature: "hide_material_tooltips(driver, blur_active=True)",
    summary: "Oculta tooltips Material que bloquean clics.",
  },
  {
    name: "ui_cleanup_state",
    platforms: ["web"],
    signature: "ui_cleanup_state(driver, timeout=3)",
    summary: "Limpia estado UI (overlays, foco) tras interacciones.",
  },
  {
    name: "legacy_click",
    platforms: ["legacy"],
    signature: "legacy_click(x, y, nombre_elemento=..., step=..., usar_create_screenshot=False, ...)",
    summary: "Clic en coordenadas de pantalla (automatización escritorio).",
  },
  {
    name: "legacy_capture_screen",
    platforms: ["legacy"],
    signature: "legacy_capture_screen(step, nombre_elemento=..., usar_create_screenshot=False)",
    summary: "Captura pantalla completa en pruebas legacy.",
  },
  {
    name: "activate_window_by_title_contains",
    platforms: ["legacy"],
    signature: "activate_window_by_title_contains(titulo_parcial, ...)",
    summary: "Activa ventana Windows cuyo título contiene el texto.",
  },
  {
    name: "set_global_evidence_config",
    platforms: ["all"],
    signature: "set_global_evidence_config(take=False, dir_name=..., func=None)",
    summary: "Configura evidencias thread-local para el escenario actual.",
  },
];

export function catalogByName(name: string): PageFunctionEntry | undefined {
  return PAGE_FUNCTIONS_CATALOG.find((e) => e.name === name);
}

export function catalogMatches(prefix: string): PageFunctionEntry[] {
  const lower = prefix.toLowerCase();
  if (!lower) return PAGE_FUNCTIONS_CATALOG;
  return PAGE_FUNCTIONS_CATALOG.filter(
    (e) => e.name.toLowerCase().includes(lower) || e.name.toLowerCase().startsWith(lower),
  );
}
