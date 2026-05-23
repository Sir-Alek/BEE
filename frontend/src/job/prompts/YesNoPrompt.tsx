import React from "react";
import { sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "yes_no" | "yes_no_cancel" }>;
};

export function YesNoPrompt(props: Props) {
  const { c, jobId, activePrompt } = props;
  const showCancel = activePrompt.type === "yes_no_cancel";
  return (
    <div style={{ display: "flex", gap: 10 }}>
      <button
        onClick={async () => {
          await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: true });
        }}
        style={{
          padding: "10px 14px",
          borderRadius: 10,
          background: c.primary,
          color: c.primaryFg,
          border: "none",
          cursor: "pointer",
        }}
      >
        Sí
      </button>
      <button
        onClick={async () => {
          await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: false });
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
        No
      </button>
      {showCancel && (
        <button
          onClick={async () => {
            await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: null });
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
      )}
    </div>
  );
}
