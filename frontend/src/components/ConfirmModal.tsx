import React from "react";

type Props = {
  c: Record<string, string>;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmModal(props: Props) {
  const {
    c,
    title,
    message,
    confirmLabel = "Confirmar",
    cancelLabel = "Cancelar",
    destructive = false,
    onConfirm,
    onCancel,
  } = props;

  return (
    <div
      data-testid="elia-confirm-modal"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1100,
        padding: 16,
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: c.surface,
          border: `1px solid ${c.border}`,
          borderRadius: 14,
          padding: "22px 24px",
          maxWidth: 440,
          width: "100%",
          boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontWeight: 800, fontSize: 16, color: c.text, marginBottom: 10 }}>{title}</div>
        <div style={{ fontSize: 14, color: c.muted, lineHeight: 1.5, marginBottom: 20, whiteSpace: "pre-wrap" }}>
          {message}
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={onCancel}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              background: c.btnGhostBg,
              color: c.text,
              border: `1px solid ${c.btnGhostBorder}`,
              cursor: "pointer",
            }}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              background: destructive ? "#c0392b" : c.primary,
              color: destructive ? "#fff" : c.primaryFg,
              border: "none",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
