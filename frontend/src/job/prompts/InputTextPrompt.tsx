import React from "react";
import { PROMPT_ANSWER_BACK, sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { promptAllowsBack } from "../../types";
import { cancelJobFlow } from "../promptNav";
import { EliaButton } from "../../components/ui";

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
        className="elia-input"
        value={textValue}
        onChange={(e) => setTextValue(e.target.value)}
        placeholder={activePrompt.message}
        style={{ width: "100%" }}
      />
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <EliaButton
          variant="primary"
          size="sm"
          onClick={async () => {
            const value = textValue.trim();
            await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: value });
          }}
        >
          Guardar
        </EliaButton>
        {promptAllowsBack(activePrompt.payload) && (
          <EliaButton
            variant="ghost"
            size="sm"
            onClick={async () => {
              await sendPromptResponse({
                jobId,
                promptId: activePrompt.prompt_id,
                answer: PROMPT_ANSWER_BACK,
              });
            }}
          >
            Regresar
          </EliaButton>
        )}
        <EliaButton
          variant="ghost"
          size="sm"
          onClick={() => {
            void cancelJobFlow(jobId);
          }}
          style={{ color: c.muted }}
        >
          Cancelar
        </EliaButton>
      </div>
    </div>
  );
}
