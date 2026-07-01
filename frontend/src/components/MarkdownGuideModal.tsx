import React from "react";
import { LoadingStatusRow } from "./LoadingStatusRow";

type Props = {
  c: Record<string, string>;
  title: string;
  subtitle?: React.ReactNode;
  content: string;
  loading?: boolean;
  error?: string | null;
  onClose: () => void;
  testId?: string;
};

export function MarkdownGuideModal(props: Props) {
  const { c, title, subtitle, content, loading, error, onClose, testId = "elia-markdown-guide-modal" } = props;

  return (
    <div
      data-testid={testId}
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
            {subtitle ? (
              <div style={{ fontSize: 12, color: c.muted, marginTop: 4 }}>{subtitle}</div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              border: `1px solid ${c.border}`,
              background: c.inputBg,
              color: c.text,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Cerrar
          </button>
        </div>
        <div style={{ flex: 1, overflow: "auto", padding: "16px 20px 20px" }}>
          {loading ? (
            <LoadingStatusRow c={c} text="Cargando guía…" loading testId={`${testId}-loading`} />
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
