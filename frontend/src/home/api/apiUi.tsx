import React, { useMemo, useState } from "react";

export type HeaderRow = { key: string; value: string };
export type EnvVarRow = { key: string; value: string };

export function parseEnvVarsJson(text: string): { ok: true; vars: Record<string, string> } | { ok: false; error: string } {
  try {
    const parsed = JSON.parse(text) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { ok: false, error: "Debe ser un objeto JSON" };
    }
    const vars = Object.fromEntries(
      Object.entries(parsed as Record<string, unknown>).map(([k, v]) => [k, String(v ?? "")]),
    );
    return { ok: true, vars };
  } catch (e: unknown) {
    return { ok: false, error: String((e as Error)?.message ?? e) };
  }
}

export function envVarsToRows(vars: Record<string, string>): EnvVarRow[] {
  const rows = Object.entries(vars).map(([key, value]) => ({ key, value }));
  return rows.length ? rows : [{ key: "", value: "" }];
}

export function rowsToEnvVarsJson(rows: EnvVarRow[]): string {
  const vars = Object.fromEntries(rows.filter((r) => r.key.trim()).map((r) => [r.key.trim(), r.value]));
  return JSON.stringify(vars, null, 2);
}

export function interpolateTemplate(text: string, vars: Record<string, string>): string {
  return String(text || "").replace(/\{\{\s*([^}]+?)\s*\}\}/g, (_, raw: string) => {
    const key = raw.trim();
    return Object.prototype.hasOwnProperty.call(vars, key) ? vars[key] : `{{${key}}}`;
  });
}

export function ApiSection(props: { c: Record<string, string>; title: string; children: React.ReactNode }) {
  const { c, title, children } = props;
  return (
    <div
      style={{
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        padding: 14,
        marginBottom: 14,
        background: c.surface,
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );
}

type ApiCollapsibleSectionProps = {
  c: Record<string, string>;
  title: string;
  subtitle?: string;
  defaultCollapsed?: boolean;
  maxListHeight?: string;
  children: React.ReactNode;
};

/** Sección colapsable con lista scrollable (evita empujar el resto del panel). */
export function ApiCollapsibleSection(props: ApiCollapsibleSectionProps) {
  const { c, title, subtitle, defaultCollapsed = false, maxListHeight = "min(280px, 38vh)", children } = props;
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <div
      style={{
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        marginBottom: 14,
        background: c.surface,
        overflow: "hidden",
      }}
    >
      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "12px 14px",
          border: "none",
          background: c.neutralBg ?? c.surface,
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span style={{ fontSize: 12, color: c.muted, width: 14 }}>{collapsed ? "▸" : "▾"}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 13, color: c.text }}>{title}</div>
          {subtitle ? (
            <div style={{ fontSize: 11, color: c.muted, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis" }}>
              {subtitle}
            </div>
          ) : null}
        </div>
      </button>
      {!collapsed ? (
        <div style={{ padding: "0 14px 14px", borderTop: `1px solid ${c.border}` }}>
          <div style={{ maxHeight: maxListHeight, overflowY: "auto", overflowX: "hidden", paddingTop: 10, paddingRight: 4 }}>
            {children}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function HeaderEditor(props: {
  c: Record<string, string>;
  rows: HeaderRow[];
  onChange: (rows: HeaderRow[]) => void;
  label: string;
  collapsible?: boolean;
  collapseThreshold?: number;
}) {
  const { c, rows, onChange, label, collapsible = false, collapseThreshold = 4 } = props;
  const filledCount = rows.filter((r) => r.key.trim()).length;
  const [open, setOpen] = useState(!collapsible || filledCount <= collapseThreshold);

  const editor = (
    <>
      {rows.map((row, idx) => (
        <div key={idx} style={{ display: "flex", gap: 8, marginBottom: 6, flexWrap: "wrap", alignItems: "center" }}>
          <input
            value={row.key}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], key: e.target.value };
              onChange(next);
            }}
            placeholder="Header"
            style={apiInputStyle(c, { flex: "1 1 140px" })}
          />
          <input
            value={row.value}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], value: e.target.value };
              onChange(next);
            }}
            placeholder="Valor"
            style={apiInputStyle(c, { flex: "2 1 200px" })}
          />
          <button
            type="button"
            title="Eliminar header"
            aria-label="Eliminar header"
            onClick={() => {
              const next = rows.filter((_, i) => i !== idx);
              onChange(next.length ? next : [{ key: "", value: "" }]);
            }}
            style={apiBtn(c, undefined, undefined, true)}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...rows, { key: "", value: "" }])}
        style={apiBtn(c, undefined, undefined, true)}
      >
        + Header
      </button>
    </>
  );

  return (
    <div style={{ marginTop: 8 }}>
      {collapsible ? (
        <details open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
          <summary style={{ cursor: "pointer", fontSize: 12, color: c.muted, marginBottom: 6, userSelect: "none" }}>
            {label} ({filledCount})
          </summary>
          {editor}
        </details>
      ) : (
        <>
          <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>{label}</div>
          {editor}
        </>
      )}
    </div>
  );
}

export function EnvVarEditor(props: {
  c: Record<string, string>;
  envVarsText: string;
  onEnvVarsTextChange: (value: string) => void;
  previewUrl?: string;
}) {
  const { c, envVarsText, onEnvVarsTextChange, previewUrl = "" } = props;
  const [jsonMode, setJsonMode] = useState(false);
  const parsed = useMemo(() => parseEnvVarsJson(envVarsText), [envVarsText]);
  const rows = parsed.ok ? envVarsToRows(parsed.vars) : [{ key: "", value: "" }];
  const resolvedUrl = parsed.ok && previewUrl.trim() ? interpolateTemplate(previewUrl, parsed.vars) : "";

  const updateRows = (nextRows: EnvVarRow[]) => {
    onEnvVarsTextChange(rowsToEnvVarsJson(nextRows));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ fontSize: 12, color: c.muted }}>Variables del entorno</div>
        <button type="button" onClick={() => setJsonMode((v) => !v)} style={apiBtn(c, undefined, undefined, true)}>
          {jsonMode ? "Vista tabla" : "Editar JSON"}
        </button>
      </div>
      {!parsed.ok ? (
        <div style={{ fontSize: 12, color: "#c0392b" }}>JSON inválido: {parsed.error}</div>
      ) : null}
      {jsonMode ? (
        <textarea
          value={envVarsText}
          onChange={(e) => onEnvVarsTextChange(e.target.value)}
          rows={8}
          style={apiMonoArea(c)}
          placeholder='{"base_url": "https://api.ejemplo.com"}'
        />
      ) : (
        <>
          {rows.map((row, idx) => (
            <div key={idx} style={{ display: "flex", gap: 8, marginBottom: 6, flexWrap: "wrap", alignItems: "center" }}>
              <input
                value={row.key}
                onChange={(e) => {
                  const next = [...rows];
                  next[idx] = { ...next[idx], key: e.target.value };
                  updateRows(next);
                }}
                placeholder="variable"
                style={apiInputStyle(c, { flex: "1 1 140px" })}
              />
              <input
                value={row.value}
                onChange={(e) => {
                  const next = [...rows];
                  next[idx] = { ...next[idx], value: e.target.value };
                  updateRows(next);
                }}
                placeholder="valor"
                style={apiInputStyle(c, { flex: "2 1 200px" })}
              />
              <button
                type="button"
                title="Eliminar variable"
                aria-label="Eliminar variable"
                onClick={() => {
                  const next = rows.filter((_, i) => i !== idx);
                  updateRows(next.length ? next : [{ key: "", value: "" }]);
                }}
                style={apiBtn(c, undefined, undefined, true)}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => updateRows([...rows, { key: "", value: "" }])}
            style={apiBtn(c, undefined, undefined, true)}
          >
            + Variable
          </button>
        </>
      )}
      {parsed.ok && Object.keys(parsed.vars).length > 0 ? (
        <div
          style={{
            padding: "10px 12px",
            borderRadius: 10,
            border: `1px solid ${c.border}`,
            background: c.inputBg,
            fontSize: 12,
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 8, color: c.text }}>Vista previa</div>
          <div style={{ color: c.muted, marginBottom: 6 }}>Variables activas ({Object.keys(parsed.vars).length})</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: previewUrl.trim() ? 10 : 0 }}>
            {Object.entries(parsed.vars).map(([key, value]) => (
              <div key={key} style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all" }}>
                <span style={{ color: c.primary }}>{key}</span>
                <span style={{ color: c.muted }}> = </span>
                <span style={{ color: c.text }}>{value || '""'}</span>
              </div>
            ))}
          </div>
          {previewUrl.trim() ? (
            <div>
              <div style={{ color: c.muted, marginBottom: 4 }}>URL resuelta (petición actual)</div>
              <div style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all", color: c.text }}>{resolvedUrl}</div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function apiInputStyle(c: Record<string, string>, extra?: React.CSSProperties): React.CSSProperties {
  return {
    padding: "8px 10px",
    borderRadius: 8,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    ...extra,
  };
}

export function apiMonoArea(c: Record<string, string>): React.CSSProperties {
  return {
    width: "100%",
    boxSizing: "border-box",
    padding: "10px 12px",
    borderRadius: 10,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    fontFamily: "monospace",
    fontSize: 13,
  };
}

export function apiBtn(
  c: Record<string, string>,
  bg?: string,
  fg?: string,
  ghost?: boolean,
): React.CSSProperties {
  return {
    padding: "8px 12px",
    borderRadius: 8,
    border: bg || ghost ? (bg ? "none" : `1px solid ${c.btnGhostBorder}`) : `1px solid ${c.btnGhostBorder}`,
    background: bg ?? c.btnGhostBg,
    color: fg ?? c.text,
    fontWeight: 600,
    cursor: "pointer",
    fontSize: 13,
  };
}
