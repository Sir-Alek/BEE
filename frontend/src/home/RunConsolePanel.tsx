import React, { useCallback, useEffect, useRef, useState } from "react";
import { getProjectReportUrl, getRunDiagnostic, getTestRun, openProjectFolder, type RunDiagnosticResponse } from "../api";
import { closeWithoutStoppingServer } from "../app/sessionGuard";
import { useAutoDismissHint } from "../hooks/useAutoDismissHint";
import { RunDiagnosticPanel } from "./RunDiagnosticPanel";
import { RunHistoryPanel } from "./RunHistoryPanel";

export type RunArtifact = {
  kind: string;
  name: string;
  path: string;
  absolute_path?: string;
};

type Props = {
  c: Record<string, string>;
  runId: string;
  platform: string;
  project: string;
  onClose: () => void;
};

const MIN_CONSOLE_H = 120;
const MAX_CONSOLE_H = 560;
const DEFAULT_CONSOLE_H = 260;

export function RunConsolePanel(props: Props) {
  const { c, runId, platform, project, onClose } = props;
  const [lines, setLines] = useState<string[]>([]);
  const [state, setState] = useState("running");
  const [returnCode, setReturnCode] = useState<number | null>(null);
  const [serverOffline, setServerOffline] = useState(false);
  const [artifacts, setArtifacts] = useState<RunArtifact[]>([]);
  const [selectedPdf, setSelectedPdf] = useState<string>("");
  const [consoleHeight, setConsoleHeight] = useState(DEFAULT_CONSOLE_H);
  const [reportFolder, setReportFolder] = useState<string>("");
  const [outputsHint, setOutputsHint] = useAutoDismissHint();
  const [diagnostic, setDiagnostic] = useState<RunDiagnosticResponse | null>(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const resizeRef = useRef<{ startY: number; startH: number } | null>(null);

  useEffect(() => {
    let closed = false;
    const es = new EventSource(`/api/runs/${encodeURIComponent(runId)}/stream`);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as {
          line?: string;
          done?: boolean;
          return_code?: number;
          state?: string;
          artifacts?: RunArtifact[];
          diagnostic?: RunDiagnosticResponse;
        };
        if (data.line) {
          setLines((prev) => [...prev, data.line as string]);
        }
        if (data.done) {
          setState(data.state ?? "done");
          setReturnCode(data.return_code ?? null);
          if (data.diagnostic) setDiagnostic(data.diagnostic);
          setHistoryRefresh((n) => n + 1);
          if (data.artifacts?.length) {
            setArtifacts(data.artifacts);
            setSelectedPdf(data.artifacts[0].name);
          }
          es.close();
        }
      } catch {
        // ignore malformed events
      }
    };
    es.onerror = () => {
      if (!closed) {
        void getTestRun(runId).then((r) => {
          setState(r.state);
          setReturnCode(r.return_code);
          setLines(r.lines ?? []);
          if (r.artifacts?.length) {
            setArtifacts(r.artifacts);
            setSelectedPdf(r.artifacts[0].name);
          }
        }).catch(() => {
          setServerOffline(true);
          closeWithoutStoppingServer();
        });
        es.close();
      }
    };
    return () => {
      closed = true;
      es.close();
    };
  }, [runId]);

  useEffect(() => {
    if (state !== "running") return;
    const poll = window.setInterval(() => {
      void getTestRun(runId)
        .then((r) => {
          if (r.state === "running") return;
          setState(r.state);
          setReturnCode(r.return_code);
          if (r.lines?.length) setLines(r.lines);
          if (r.artifacts?.length) {
            setArtifacts(r.artifacts);
            setSelectedPdf((prev) => prev || r.artifacts![0].name);
          }
        })
        .catch(() => {
          setServerOffline(true);
          closeWithoutStoppingServer();
        });
    }, 2000);
    return () => window.clearInterval(poll);
  }, [runId, state]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  useEffect(() => {
    if (!project.trim() || state === "running") return;
    void getTestRun(runId).then((r) => {
      if (r.artifacts?.length) {
        setArtifacts(r.artifacts);
        setSelectedPdf((prev) => prev || r.artifacts![0].name);
      }
    });
  }, [runId, project, state]);

  const passed = state === "done" && returnCode === 0;
  const statusLabel = serverOffline
    ? "Servidor desconectado"
    : passed
      ? "✓ Aprobado"
      : state === "running"
        ? "En curso…"
        : "✗ Fallido";
  const pdfPreviewUrl =
    selectedPdf && platform && project ? getProjectReportUrl(platform, project, selectedPdf) : "";

  useEffect(() => {
    if (state === "running" || passed) return;
    void getRunDiagnostic(runId)
      .then((r) => setDiagnostic(r.diagnostic))
      .catch(() => undefined);
  }, [runId, state, passed]);

  const onResizeStart = useCallback(
    (ev: React.MouseEvent) => {
      ev.preventDefault();
      resizeRef.current = { startY: ev.clientY, startH: consoleHeight };
      const onMove = (moveEv: MouseEvent) => {
        if (!resizeRef.current) return;
        const delta = resizeRef.current.startY - moveEv.clientY;
        const next = Math.min(MAX_CONSOLE_H, Math.max(MIN_CONSOLE_H, resizeRef.current.startH + delta));
        setConsoleHeight(next);
      };
      const onUp = () => {
        resizeRef.current = null;
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    [consoleHeight],
  );

  return (
    <div
      data-testid="elia-run-console"
      style={{
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        padding: 14,
        background: c.inputBg,
        marginTop: 12,
      }}
    >
      <div
        role="separator"
        aria-label="Redimensionar consola"
        onMouseDown={onResizeStart}
        style={{
          height: 6,
          margin: "-8px 0 10px",
          cursor: "row-resize",
          borderRadius: 4,
          background: c.border,
        }}
      />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
        <div style={{ fontWeight: 700 }}>
          Consola de ejecución — {statusLabel}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            type="button"
            onClick={onClose}
            style={{ border: "none", background: "transparent", color: c.primary, cursor: "pointer" }}
          >
            Cerrar
          </button>
        </div>
      </div>

      <pre
        style={{
          margin: 0,
          height: consoleHeight,
          overflow: "auto",
          fontSize: 12,
          lineHeight: 1.45,
          color: c.text,
          whiteSpace: "pre-wrap",
          fontFamily: '"Cascadia Code", Consolas, monospace',
          border: `1px solid ${c.border}`,
          borderRadius: 8,
          padding: 10,
          background: c.surface,
        }}
      >
        {lines.join("\n") || "Esperando salida…"}
      </pre>
      <div ref={bottomRef} />

      {!passed && state !== "running" && diagnostic && platform && project ? (
        <RunDiagnosticPanel c={c} platform={platform} project={project} diagnostic={diagnostic} />
      ) : null}

      {state !== "running" ? (
        <div
          data-testid="elia-run-report-panel"
          style={{
            marginTop: 14,
            borderTop: `1px solid ${c.border}`,
            paddingTop: 14,
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Reporte PDF de ejecución</div>
          {artifacts.length === 0 ? (
            <div style={{ fontSize: 13, color: c.muted, marginBottom: 8 }}>
              No se detectó PDF en <code style={{ fontSize: 12 }}>outputs/pdfReports</code>. Revisa la consola o abre{" "}
              <code style={{ fontSize: 12 }}>outputs</code> del proyecto (logs, PDF y evidencias).
            </div>
          ) : (
            <>
              {artifacts.length > 1 ? (
                <select
                  value={selectedPdf}
                  onChange={(e) => setSelectedPdf(e.target.value)}
                  style={{
                    marginBottom: 10,
                    padding: "6px 10px",
                    borderRadius: 8,
                    border: `1px solid ${c.inputBorder}`,
                    background: c.inputBg,
                    color: c.text,
                    fontSize: 13,
                  }}
                >
                  {artifacts.map((a) => (
                    <option key={a.name} value={a.name}>
                      {a.name}
                    </option>
                  ))}
                </select>
              ) : (
                <div style={{ fontSize: 13, color: c.muted, marginBottom: 8 }}>{selectedPdf}</div>
              )}

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
                <a
                  href={pdfPreviewUrl}
                  download={selectedPdf}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    background: c.primary,
                    color: c.primaryFg,
                    textDecoration: "none",
                    fontWeight: 600,
                    fontSize: 13,
                  }}
                >
                  Descargar PDF
                </a>
                <button
                  type="button"
                  onClick={() => {
                    void openProjectFolder(platform, project, "outputs").then((r) => {
                      setReportFolder(r.path);
                      setOutputsHint(
                        r.hint ?? "Si no ves la ventana del explorador, revísala en la barra de tareas.",
                      );
                    });
                  }}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: `1px solid ${c.btnGhostBorder}`,
                    background: c.btnGhostBg,
                    color: c.text,
                    cursor: "pointer",
                    fontWeight: 600,
                    fontSize: 13,
                  }}
                >
                  Abrir carpeta outputs
                </button>
              </div>

              <div
                style={{
                  border: `1px solid ${c.border}`,
                  borderRadius: 10,
                  overflow: "hidden",
                  background: c.surface,
                  minHeight: 360,
                }}
              >
                <iframe title="Vista previa PDF" src={pdfPreviewUrl} style={{ width: "100%", height: 420, border: "none" }} />
              </div>
            </>
          )}
          {reportFolder || outputsHint ? (
            <div style={{ fontSize: 12, color: c.muted, marginTop: 8 }}>
              {reportFolder ? (
                <>
                  Carpeta: <code>{reportFolder}</code>
                  {outputsHint ? <div style={{ marginTop: 4 }}>{outputsHint}</div> : null}
                </>
              ) : (
                outputsHint
              )}
            </div>
          ) : null}
        </div>
      ) : null}

      {platform && project ? (
        <RunHistoryPanel
          c={c}
          platform={platform}
          project={project}
          activeRunId={state !== "running" ? runId : null}
          refreshToken={historyRefresh}
          onSelectDiagnostic={(entry) => setDiagnostic(entry)}
        />
      ) : null}
    </div>
  );
}
