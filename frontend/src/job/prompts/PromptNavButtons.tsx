import React from "react";
import { cancelJobFlow, goBackPrompt } from "../promptNav";

type Props = {
  c: Record<string, string>;
  jobId: string;
  promptId: string;
  showBack?: boolean;
};

export function PromptNavButtons(props: Props) {
  const { c, jobId, promptId, showBack = false } = props;
  return (
    <div
      style={{
        display: "flex",
        gap: 10,
        flexWrap: "wrap",
        marginTop: 14,
        paddingTop: 12,
        borderTop: `1px solid ${c.border}`,
      }}
    >
      {showBack ? (
        <button
          type="button"
          onClick={() => {
            void goBackPrompt(jobId, promptId);
          }}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: c.btnGhostBg,
            color: c.text,
            border: `1px solid ${c.btnGhostBorder}`,
            cursor: "pointer",
          }}
        >
          Regresar
        </button>
      ) : null}
      <button
        type="button"
        onClick={() => {
          void cancelJobFlow(jobId);
        }}
        style={{
          padding: "10px 14px",
          borderRadius: 10,
          background: c.btnGhostBg,
          color: c.muted,
          border: `1px solid ${c.btnGhostBorder}`,
          cursor: "pointer",
        }}
      >
        Cancelar
      </button>
    </div>
  );
}
