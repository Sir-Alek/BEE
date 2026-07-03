import React, { useMemo, useState } from "react";
import { sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { EliaButton } from "../../components/ui";

type RecordingOptionDef = {
  key: string;
  label: string;
  default?: boolean;
};

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "recording_options" }>;
};

function initialSelections(options: RecordingOptionDef[]): Record<string, boolean> {
  const out: Record<string, boolean> = {};
  for (const opt of options) {
    out[opt.key] = Boolean(opt.default);
  }
  return out;
}

export function RecordingOptionsPrompt(props: Props) {
  const { c, jobId, activePrompt } = props;
  const options = activePrompt.payload?.options ?? [];
  const [selected, setSelected] = useState(() => initialSelections(options));

  const answer = useMemo(
    () => ({
      video: Boolean(selected.video),
      capture_api: Boolean(selected.capture_api),
    }),
    [selected],
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {options.map((opt) => (
          <label
            key={opt.key}
            style={{
              display: "flex",
              gap: 10,
              alignItems: "flex-start",
              cursor: "pointer",
              fontSize: 14,
              color: c.text,
            }}
          >
            <input
              type="checkbox"
              checked={Boolean(selected[opt.key])}
              onChange={(e) =>
                setSelected((prev) => ({
                  ...prev,
                  [opt.key]: e.target.checked,
                }))
              }
              style={{ marginTop: 3 }}
            />
            <span>{opt.label}</span>
          </label>
        ))}
      </div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <EliaButton
          variant="primary"
          size="sm"
          onClick={async () => {
            await sendPromptResponse({ jobId, promptId: activePrompt.prompt_id, answer });
          }}
        >
          Continuar
        </EliaButton>
      </div>
    </div>
  );
}
