import React from "react";
import { sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { EliaButton } from "../../components/ui";

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
        <EliaButton
          key={opt.value}
          variant="ghost"
          size="sm"
          onClick={async () => {
            await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: opt.value });
          }}
          style={{ textAlign: "left", justifyContent: "flex-start" }}
        >
          {opt.label}
        </EliaButton>
      ))}
    </div>
  );
}
