import React from "react";

type Props = {
  c: Record<string, string>;
  text: string;
  testId?: string;
  loading?: boolean;
  tone?: "neutral" | "success" | "error" | "info";
};

/** Fila de estado con spinner unificado (módulos, API, móvil). */
export function LoadingStatusRow(props: Props) {
  const { text, testId, loading = false, tone = "neutral" } = props;
  const toneClass =
    tone === "error"
      ? " elia-loading-row--error"
      : tone === "success"
        ? " elia-loading-row--success"
        : tone === "info" || loading
          ? " elia-loading-row--info"
          : "";

  return (
    <div role="status" data-testid={testId} className={`elia-loading-row${toneClass}`}>
      {loading ? <span className="elia-spinner" aria-hidden /> : null}
      <span>{text}</span>
    </div>
  );
}
