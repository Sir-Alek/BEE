import React from "react";

type Props = {
  c: Record<string, string>;
  title?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
};

export function SecondaryToolbar(props: Props) {
  const { c, title, children, style } = props;
  return (
    <div
      style={{
        marginTop: 16,
        paddingTop: 14,
        borderTop: `1px solid ${c.border}`,
        ...style,
      }}
    >
      {title ? (
        <div style={{ fontSize: 12, color: c.muted, marginBottom: 10, fontWeight: 600 }}>{title}</div>
      ) : null}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 10,
          alignItems: "center",
          padding: "10px 12px",
          borderRadius: 10,
          border: `1px dashed ${c.border}`,
          background: c.toolbarBg,
        }}
      >
        {children}
      </div>
    </div>
  );
}

export function OutlinedButton(props: {
  c: Record<string, string>;
  children: React.ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  testId?: string;
}) {
  const { c, children, disabled, onClick, testId } = props;
  return (
    <button
      type="button"
      data-testid={testId}
      disabled={disabled}
      onClick={onClick}
      style={{
        padding: "7px 12px",
        borderRadius: 8,
        background: "transparent",
        color: disabled ? c.muted : c.text,
        border: `1px solid ${c.btnGhostBorder}`,
        fontSize: 13,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.55 : 1,
      }}
    >
      {children}
    </button>
  );
}
