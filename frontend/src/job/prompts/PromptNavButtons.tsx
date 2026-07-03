import React from "react";
import { cancelJobFlow, goBackPrompt } from "../promptNav";
import { EliaButton } from "../../components/ui";

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
        <EliaButton
          variant="ghost"
          size="sm"
          onClick={() => {
            void goBackPrompt(jobId, promptId);
          }}
        >
          Regresar
        </EliaButton>
      ) : null}
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
  );
}
