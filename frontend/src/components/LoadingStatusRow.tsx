import React from "react";

const spinnerStyle = (c: Record<string, string>): React.CSSProperties => ({
  width: 14,
  height: 14,
  borderRadius: "50%",
  border: `2px solid ${c.border}`,
  borderTopColor: c.primary,
  animation: "elia-spin 0.8s linear infinite",
  flexShrink: 0,
});

type Props = {
  c: Record<string, string>;
  text: string;
  testId?: string;
  loading?: boolean;
  tone?: "neutral" | "success" | "error";
};

/** Fila de estado con spinner unificado (módulos, API, móvil). */
export function LoadingStatusRow(props: Props) {
  const { c, text, testId, loading = false, tone = "neutral" } = props;
  const isError = tone === "error";
  const isSuccess = tone === "success";

  return (
    <div
      role="status"
      data-testid={testId}
      style={{
        background: isError ? c.errorBg : isSuccess ? c.hintBg : c.hintBg,
        border: `1px solid ${isError ? c.errorBorder : isSuccess ? c.hintBorder : c.hintBorder}`,
        color: isError ? c.errorTitle : c.hintText,
        padding: "10px 14px",
        borderRadius: 10,
        marginBottom: 10,
        fontSize: 13,
        display: "flex",
        alignItems: "center",
        gap: 8,
        lineHeight: 1.45,
      }}
    >
      {loading ? <span aria-hidden style={spinnerStyle(c)} /> : null}
      <span>{text}</span>
    </div>
  );
}
