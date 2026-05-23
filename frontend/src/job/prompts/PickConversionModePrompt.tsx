import React from "react";
import { sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "pick_conversion_mode" }>;
};

export function PickConversionModePrompt(props: Props) {
  const { c, jobId, activePrompt } = props;
  if (!activePrompt.options) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {activePrompt.options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={async () => {
            await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: opt.value });
          }}
          style={{
            padding: "12px 14px",
            borderRadius: 10,
            background: c.btnGhostBg,
            color: c.text,
            border: `1px solid ${c.btnGhostBorder}`,
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
