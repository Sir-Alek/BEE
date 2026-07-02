import React from "react";

type Props = {
  c: Record<string, string>;
  message: string | null;
  testId?: string;
};

/** Aviso breve justo debajo del control que lo disparó (p. ej. «Abrir carpeta»). */
export function InlineActionHint(props: Props) {
  const { c, message, testId } = props;
  if (!message?.trim()) return null;
  return (
    <div
      data-testid={testId}
      role="status"
      style={{
        marginTop: 6,
        padding: "6px 10px",
        borderRadius: 8,
        background: c.hintBg,
        border: `1px solid ${c.hintBorder}`,
        color: c.hintText,
        fontSize: 12,
        lineHeight: 1.45,
      }}
    >
      {message}
    </div>
  );
}
