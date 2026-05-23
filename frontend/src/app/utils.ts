export function formatPromptType(t: string): string {
  if (t === "message_ack") return "Aviso";
  return t.replaceAll("_", " ");
}

export function formatJobMode(mode: string | null): string {
  if (!mode) return "";
  if (mode === "puppeteer_recorder") return "Grabar interacciones";
  if (mode === "puppeteer_to_behave") return "Convertir a Behave";
  if (mode === "puppeteer_to_step_by_step") return "Convertir a step by step";
  if (mode === "elia_jira_smoke") return "ELIA · Conectar a Jira";
  if (mode === "elia_value_edge_smoke") return "ELIA · Extraer de ValueEdge";
  if (mode === "elia_gherkin_batch") return "ELIA · Procesamiento por lotes (Gherkin)";
  if (mode === "mobile_recorder") return "Grabar interacciones (Móvil)";
  if (mode === "legacy_recorder") return "Grabar interacciones (Legacy)";
  if (mode === "mobile_to_behave") return "Convertir a Behave (Móvil)";
  if (mode === "legacy_to_behave") return "Convertir a Behave (Legacy)";
  if (mode === "doc_to_bdd") return "ELIA · Procesar y Convertir a BDD";
  return mode;
}

export function openJobUrlInNewTabPrepared(): Window | null {
  return window.open("about:blank", "_blank");
}

export function goHomeInThisTab(): void {
  window.location.assign(`${window.location.origin}/`);
}

export function modalFieldStyle(c: Record<string, string>): React.CSSProperties {
  return {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    fontSize: 14,
  };
}

export function tryFocusOpenerAndCloseThisTab(): boolean {
  if (!window.opener || window.opener.closed) {
    return false;
  }
  try {
    window.opener.focus();
  } catch {
    // ignore
  }
  try {
    window.close();
    return true;
  } catch {
    return false;
  }
}

export async function copyTextToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      /* fallback */
    }
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}
