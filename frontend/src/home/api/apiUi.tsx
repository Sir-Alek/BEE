import React from "react";

export type HeaderRow = { key: string; value: string };

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

export function HeaderEditor(props: {
  c: Record<string, string>;
  rows: HeaderRow[];
  onChange: (rows: HeaderRow[]) => void;
  label: string;
}) {
  const { c, rows, onChange, label } = props;
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>{label}</div>
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
