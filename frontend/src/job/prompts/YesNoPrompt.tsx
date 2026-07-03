import React from "react";
import { sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { EliaButton } from "../../components/ui";

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "yes_no" | "yes_no_cancel" }>;
};

export function YesNoPrompt(props: Props) {
  const { c, jobId, activePrompt } = props;
  return (
    <div style={{ display: "flex", gap: 10 }}>
      <EliaButton
        variant="primary"
        size="sm"
        onClick={async () => {
          await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: true });
        }}
      >
        Sí
      </EliaButton>
      <EliaButton
        variant="ghost"
        size="sm"
        onClick={async () => {
          await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer: false });
        }}
      >
        No
      </EliaButton>
    </div>
  );
}
