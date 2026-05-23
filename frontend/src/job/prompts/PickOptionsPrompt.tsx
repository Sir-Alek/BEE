import React from "react";
import { PROMPT_ANSWER_BACK, sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { promptAllowsBack } from "../../types";

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "pick_project" | "pick_script" }>;
};

export function PickOptionsPrompt(props: Props) {
  const { c, jobId, activePrompt } = props;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {(activePrompt.options ?? []).map((opt) => (
          <button
            key={opt.value}
            onClick={async () => {
              await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: opt.value });
            }}
            style={{
              padding: "10px 12px",
              borderRadius: 10,
              border: `1px solid ${c.btnGhostBorder}`,
              background: c.btnGhostBg,
              color: c.text,
              cursor: "pointer",
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>
      {promptAllowsBack(activePrompt.payload) && (
        <button
          type="button"
          onClick={async () => {
            await sendPromptResponse({
              jobId,
              promptId: activePrompt.prompt_id,
              answer: PROMPT_ANSWER_BACK,
            });
          }}
          style={{
            alignSelf: "flex-start",
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
      )}
    </div>
  );
}
