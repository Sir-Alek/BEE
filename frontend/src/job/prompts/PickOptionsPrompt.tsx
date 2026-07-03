import React from "react";
import { sendPromptResponse } from "../../api";
import { EliaButton } from "../../components/ui";
import type { ActivePrompt } from "../../types";

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "pick_project" | "pick_script" }>;
};

export function PickOptionsPrompt(props: Props) {
  const { jobId, activePrompt } = props;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {(activePrompt.options ?? []).map((opt) => (
          <EliaButton
            key={opt.value}
            variant="ghost"
            onClick={async () => {
              await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: opt.value });
            }}
          >
            {opt.label}
          </EliaButton>
        ))}
      </div>
    </div>
  );
}
