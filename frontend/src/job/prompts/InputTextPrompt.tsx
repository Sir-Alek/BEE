import React from "react";
import { PROMPT_ANSWER_BACK, sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { promptAllowsBack } from "../../types";
import { cancelJobFlow } from "../promptNav";

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "input_text" }>;
  textValue: string;
  setTextValue: (v: string) => void;
};

export function InputTextPrompt(props: Props) {
  const { c, jobId, activePrompt, textValue, setTextValue } = props;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <input
        value={textValue}
        onChange={(e) => setTextValue(e.target.value)}
        placeholder={activePrompt.message}
        style={{
          width: "100%",
          padding: "10px 12px",
          borderRadius: 10,
          border: `1px solid ${c.inputBorder}`,
          background: c.inputBg,
          color: c.text,
          outline: "none",
          fontSize: 14,
        }}
      />
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button
          onClick={async () => {
            const value = textValue.trim();
            await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: value });
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
          Guardar
        </button>
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
        <button
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
    </div>
  );
}
