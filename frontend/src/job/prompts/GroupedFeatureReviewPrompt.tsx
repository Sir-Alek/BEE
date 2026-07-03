import React from "react";
import { sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { cancelJobFlow } from "../promptNav";
import { EliaButton } from "../../components/ui";

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "grouped_feature_review" }>;
  bddPreviewText: string;
  setBddPreviewText: (v: string) => void;
};

export function GroupedFeatureReviewPrompt(props: Props) {
  const { c, jobId, activePrompt: ap, bddPreviewText, setBddPreviewText } = props;
  if (!ap.payload) return null;
  const names = ap.payload.script_names ?? [];
  const bg = ap.payload.background_count ?? 0;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ fontSize: 13, color: c.muted }}>
        Grabaciones: {names.join(", ") || "—"}
        {bg > 0 ? ` · Background: ${bg} paso(s)` : ""}
      </div>
      <textarea
        value={bddPreviewText}
        onChange={(e) => setBddPreviewText(e.target.value)}
        style={{
          width: "100%",
          minHeight: 280,
          padding: 10,
          borderRadius: 10,
          border: `1px solid ${c.inputBorder}`,
          fontFamily: "ui-monospace, monospace",
          fontSize: 13,
          background: c.inputBg,
          color: c.text,
        }}
      />
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        <EliaButton
          variant="primary"
          size="sm"
          onClick={async () => {
            await sendPromptResponse({
              jobId,
              promptId: ap.prompt_id,
              answer: { action: "accept", feature_text: bddPreviewText },
            });
          }}
        >
          Aceptar y generar
        </EliaButton>
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
