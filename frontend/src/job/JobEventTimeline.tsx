import React from "react";
import type { JobEvent } from "./jobEvents";
import { describeJobEvent, isRecordingTimelineEvent } from "./jobEvents";

export function JobEventTimeline(props: {
  events: JobEvent[];
  c: Record<string, string>;
  recordingOnly?: boolean;
}) {
  const { events, c, recordingOnly = false } = props;
  const filtered = recordingOnly
    ? events.filter((e) => isRecordingTimelineEvent(e.type))
    : events.filter((e) => e.type !== "ai_policy");

  if (filtered.length === 0) return null;

  return (
    <div
      data-testid="elia-job-event-timeline"
      style={{
        marginTop: 10,
        padding: "10px 12px",
        borderRadius: 10,
        border: `1px solid ${c.border}`,
        background: c.inputBg,
        maxHeight: 160,
        overflow: "auto",
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 700, color: c.muted, marginBottom: 8 }}>
        Actividad en tiempo real
      </div>
      <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, lineHeight: 1.5, color: c.text }}>
        {filtered.slice(-12).map((event, idx) => {
          const { label, detail } = describeJobEvent(event);
          return (
            <li key={`${event.type}-${event.ts ?? idx}-${idx}`} style={{ marginBottom: 4 }}>
              <span style={{ fontWeight: 600 }}>{label}</span>
              {detail ? <span style={{ color: c.muted }}> — {detail}</span> : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
