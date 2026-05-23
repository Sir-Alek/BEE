import React from "react";
import { sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { GeneratedFilesResultView } from "../jobUiComponents";
import type { JobProgressState } from "../useJobProgress";

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "message_ack" }>;
  job: JobProgressState | null;
};

export function MessageAckPrompt(props: Props) {
  const { c, jobId, activePrompt: ap, job } = props;
  const resultPayload = ap.payload ?? null;
  const hasFiles =
    Boolean(resultPayload?.generated_files?.length) ||
    Boolean(resultPayload?.output_dir || resultPayload?.project_dir);
  return (
    <div>
      {hasFiles ? (
        <GeneratedFilesResultView message={ap.message} payload={resultPayload} progress={job?.progress} c={c} />
      ) : (
        <div
          style={{
            background:
              ap.severity === "error" ? c.msgErrBg : ap.severity === "warning" ? c.msgWarnBg : c.msgInfoBg,
            border:
              ap.severity === "error"
                ? `1px solid ${c.msgErrBorder}`
                : ap.severity === "warning"
                  ? `1px solid ${c.msgWarnBorder}`
                  : `1px solid ${c.msgInfoBorder}`,
            color:
              ap.severity === "error"
                ? c.msgErrText
                : ap.severity === "warning"
                  ? c.msgWarnText
                  : c.msgInfoText,
            padding: 12,
            borderRadius: 10,
            marginBottom: 14,
            whiteSpace: "pre-wrap",
            fontSize: 14,
            maxHeight: "min(50vh, 360px)",
            overflow: "auto",
          }}
        >
          {ap.message}
        </div>
      )}
      <div
        style={{
          display: "flex",
          gap: 10,
          flexWrap: "wrap",
          marginTop: 4,
          position: "sticky",
          bottom: 0,
          background: c.stickyBarBg,
          paddingTop: 8,
        }}
      >
        <button
          type="button"
          onClick={async () => {
            await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: true });
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
          Aceptar
        </button>
        <button
          type="button"
          onClick={async () => {
            await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: true });
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
          Cerrar
        </button>
      </div>
    </div>
  );
}
