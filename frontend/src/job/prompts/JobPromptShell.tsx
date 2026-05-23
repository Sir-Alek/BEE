import React from "react";
import type { ActivePrompt } from "../../types";
import { formatPromptType } from "../../app/utils";

export type JobPromptShellProps = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: ActivePrompt;
  children: React.ReactNode;
};

export function JobPromptShell(props: JobPromptShellProps) {
  const { c, jobId, activePrompt, children } = props;
  return (
    <div
      data-testid="elia-job-prompt"
      style={{
        background: c.surface,
        border: `1px solid ${c.border}`,
        borderRadius: 14,
        padding: 18,
        boxShadow: c.shadow,
      }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        <div style={{ fontSize: 13, color: c.muted }}>{formatPromptType(activePrompt.type)}</div>
        <div style={{ marginLeft: "auto", fontSize: 12, color: c.muted }}>job: {jobId.slice(0, 8)}...</div>
      </div>
      <h2 style={{ margin: "10px 0 6px", fontSize: 20, color: c.text }}>{activePrompt.title}</h2>
      {activePrompt.type !== "message_ack" && (
        <div style={{ color: c.text, marginBottom: 14 }}>{activePrompt.message}</div>
      )}
      {children}
    </div>
  );
}
