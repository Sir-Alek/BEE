import React from "react";
import { LoadingStatusRow } from "../components/LoadingStatusRow";
import {
  getProjectRunHistoryEntry,
  listProjectRunHistory,
  type RunDiagnosticResponse,
  type RunHistoryEntry,
} from "../api";

type Props = {
  c: Record<string, string>;
  platform: string;
  project: string;
  activeRunId?: string | null;
  refreshToken?: number;
  onSelectDiagnostic?: (diagnostic: RunDiagnosticResponse, runId: string) => void;
};

function formatWhen(ts: number): string {
  try {
    return new Date(ts * 1000).toLocaleString();
  } catch {
    return String(ts);
  }
}

export function RunHistoryPanel(props: Props) {
  const { c, platform, project, activeRunId, refreshToken, onSelectDiagnostic } = props;
  const [runs, setRuns] = React.useState<RunHistoryEntry[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [expanded, setExpanded] = React.useState(true);

  React.useEffect(() => {
    if (!project.trim()) {
      setRuns([]);
      return;
    }
    setLoading(true);
    void listProjectRunHistory(platform, project)
      .then((r) => setRuns(r.runs ?? []))
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  }, [platform, project, refreshToken, activeRunId]);

  if (!project.trim()) return null;

  return (
    <div
      data-testid="elia-run-history"
      style={{
        marginTop: 14,
        borderTop: `1px solid ${c.border}`,
        paddingTop: 12,
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        style={{
          border: "none",
          background: "transparent",
          color: c.text,
          fontWeight: 700,
          cursor: "pointer",
          padding: 0,
          marginBottom: expanded ? 8 : 0,
        }}
      >
        Historial de ejecuciones {expanded ? "▾" : "▸"}
      </button>

      {expanded ? (
        loading ? (
          <LoadingStatusRow c={c} text="Cargando historial…" loading />
        ) : runs.length === 0 ? (
          <div style={{ fontSize: 13, color: c.muted }}>
            Aún no hay ejecuciones guardadas (máximo 5 por proyecto en{" "}
            <code>outputs/.elia/runs</code>).
          </div>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {runs.map((run) => {
              const failed = run.summary !== "passed";
              const isActive = activeRunId === run.run_id;
              return (
                <button
                  key={run.run_id}
                  type="button"
                  onClick={() => {
                    if (!onSelectDiagnostic) return;
                    void getProjectRunHistoryEntry(platform, project, run.run_id)
                      .then((r) => onSelectDiagnostic(r.diagnostic, run.run_id))
                      .catch(() => undefined);
                  }}
                  style={{
                    textAlign: "left",
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: `1px solid ${isActive ? c.primary : c.border}`,
                    background: isActive ? c.inputBg : c.surface,
                    cursor: onSelectDiagnostic ? "pointer" : "default",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 600, color: failed ? (c.errorTitle ?? "#c0392b") : c.text }}>
                      {failed ? "✗ Fallido" : "✓ OK"}
                    </span>
                    <span style={{ fontSize: 12, color: c.muted }}>{formatWhen(run.finished_at)}</span>
                  </div>
                  <div style={{ fontSize: 13, marginTop: 4, color: c.text }}>
                    {run.scenario || run.kind || "Ejecución"}
                  </div>
                  {run.failed_step ? (
                    <div style={{ fontSize: 12, color: c.muted, marginTop: 2 }}>
                      Paso: {run.failed_step}
                    </div>
                  ) : null}
                  {run.failure_reason ? (
                    <div
                      style={{
                        fontSize: 12,
                        color: c.muted,
                        marginTop: 2,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {run.failure_reason}
                    </div>
                  ) : null}
                </button>
              );
            })}
          </div>
        )
      ) : null}
    </div>
  );
}
