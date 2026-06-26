import React from "react";
import { apiBtn } from "./apiUi";

type Props = {
  c: Record<string, string>;
  title: string;
  content: string;
  loading?: boolean;
  error?: string | null;
  onClose: () => void;
};

export function ApiScriptsGuideModal(props: Props) {
  const { c, title, content, loading, error, onClose } = props;

  return (
    <div
      data-testid="elia-api-scripts-guide-modal"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: c.surface,
          border: `1px solid ${c.border}`,
          borderRadius: 16,
          width: "min(920px, 96vw)",
          maxHeight: "min(88vh, 900px)",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            padding: "16px 20px",
            borderBottom: `1px solid ${c.border}`,
          }}
        >
          <div>
            <div style={{ fontWeight: 800, fontSize: 16, color: c.text }}>{title}</div>
            <div style={{ fontSize: 12, color: c.muted, marginTop: 4 }}>
              Referencia de <code style={{ fontSize: 11 }}>pm.*</code> en pre-request y post-request
            </div>
          </div>
          <button type="button" onClick={onClose} style={apiBtn(c)}>
            Cerrar
          </button>
        </div>
        <div style={{ flex: 1, overflow: "auto", padding: "16px 20px 20px" }}>
          {loading ? (
            <div style={{ fontSize: 13, color: c.muted }}>Cargando guía…</div>
          ) : error ? (
            <div style={{ fontSize: 13, color: "#c0392b" }}>{error}</div>
          ) : (
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontSize: 13,
                lineHeight: 1.55,
                fontFamily: '"Segoe UI", system-ui, sans-serif',
                color: c.text,
              }}
            >
              {content}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
