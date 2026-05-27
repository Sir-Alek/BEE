import React, { useEffect, useState } from "react";
import {
  getPlatformProjects,
  listProjectFiles,
  readProjectFile,
  startUnifiedRun,
  writeProjectFile,
} from "../api";
import { RunConsolePanel } from "./RunConsolePanel";

type Props = {
  c: Record<string, string>;
  platform: "web" | "mobile" | "legacy" | "api";
  project: string;
  canRunJobs: boolean;
  onShowError: (msg: string) => void;
  showLocust?: boolean;
};

export function RunWorkspacePanel(props: Props) {
  const { c, platform, project, canRunJobs, onShowError, showLocust = platform === "api" } = props;
  const [files, setFiles] = useState<{ path: string; name: string }[]>([]);
  const [selected, setSelected] = useState("");
  const [editor, setEditor] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [featureFile, setFeatureFile] = useState("features");
  const [generatePdf, setGeneratePdf] = useState(true);
  const [loadUsers, setLoadUsers] = useState("5");

  const refreshFiles = () => {
    if (!project.trim()) return;
    void listProjectFiles(platform, project)
      .then((r) => setFiles(r.files))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  useEffect(() => {
    refreshFiles();
    setSelected("");
    setEditor("");
    setDirty(false);
  }, [platform, project]);

  const loadFile = (path: string) => {
    setBusy(true);
    void readProjectFile(platform, project, path)
      .then((r) => {
        setSelected(path);
        setEditor(r.content);
        setDirty(false);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const saveFile = () => {
    if (!selected) return;
    setBusy(true);
    void writeProjectFile(platform, project, selected, editor)
      .then(() => {
        setDirty(false);
        refreshFiles();
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const runBehave = () => {
    setBusy(true);
    void startUnifiedRun({
      platform,
      project,
      kind: "behave",
      feature_file: featureFile.trim() || "features",
      generate_evidence: generatePdf,
    })
      .then((r) => setRunId(r.run_id))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const runLocust = () => {
    setBusy(true);
    void startUnifiedRun({
      platform: "api",
      project,
      kind: "locust",
      locust_users: Number(loadUsers) || 5,
      locust_spawn_rate: 1,
      locust_run_time: "1m",
    })
      .then((r) => setRunId(r.run_id))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  if (!project.trim()) {
    return <div style={{ fontSize: 13, color: c.muted }}>Selecciona un proyecto para ejecutar y editar código.</div>;
  }

  return (
    <div data-testid="elia-run-workspace" style={{ marginTop: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>Ejecutar y editar proyecto</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10, alignItems: "center" }}>
        <input
          value={featureFile}
          onChange={(e) => setFeatureFile(e.target.value)}
          placeholder="features o features/mi.feature"
          style={{ flex: "1 1 200px", padding: "8px 10px", borderRadius: 8, border: `1px solid ${c.inputBorder}` }}
        />
        <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
          <input type="checkbox" checked={generatePdf} onChange={(e) => setGeneratePdf(e.target.checked)} />
          PDF + logo ELIA
        </label>
        <button type="button" disabled={!canRunJobs || busy} onClick={runBehave} style={btn(c, c.primary, c.primaryFg)}>
          Ejecutar Behave
        </button>
        {showLocust ? (
          <>
            <input
              value={loadUsers}
              onChange={(e) => setLoadUsers(e.target.value)}
              style={{ width: 70, padding: "8px 10px", borderRadius: 8, border: `1px solid ${c.inputBorder}` }}
            />
            <button type="button" disabled={!canRunJobs || busy} onClick={runLocust} style={btn(c)}>
              Ejecutar Locust
            </button>
          </>
        ) : null}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(160px, 220px) 1fr", gap: 10, marginBottom: 12 }}>
        <div
          style={{
            border: `1px solid ${c.border}`,
            borderRadius: 10,
            maxHeight: 220,
            overflow: "auto",
            fontSize: 12,
            background: c.surface,
          }}
        >
          {files.length === 0 ? (
            <div style={{ padding: 10, color: c.muted }}>Sin archivos editables</div>
          ) : (
            files.map((f) => (
              <button
                key={f.path}
                type="button"
                onClick={() => loadFile(f.path)}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "8px 10px",
                  border: "none",
                  borderBottom: `1px solid ${c.border}`,
                  background: selected === f.path ? c.neutralBg : "transparent",
                  color: c.text,
                  cursor: "pointer",
                }}
              >
                {f.path}
              </button>
            ))
          )}
        </div>
        <div>
          <textarea
            value={editor}
            onChange={(e) => {
              setEditor(e.target.value);
              setDirty(true);
            }}
            placeholder="Selecciona un .feature, .py o locustfile.py para editar"
            rows={10}
            style={{
              width: "100%",
              boxSizing: "border-box",
              fontFamily: "monospace",
              fontSize: 12,
              padding: 10,
              borderRadius: 10,
              border: `1px solid ${c.inputBorder}`,
              background: c.inputBg,
              color: c.text,
            }}
          />
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <button type="button" disabled={!selected || !dirty || busy} onClick={saveFile} style={btn(c)}>
              Guardar archivo
            </button>
            <button type="button" disabled={!selected || busy} onClick={() => loadFile(selected)} style={btn(c)}>
              Recargar
            </button>
          </div>
        </div>
      </div>

      {runId ? <RunConsolePanel c={c} runId={runId} onClose={() => setRunId(null)} /> : null}
    </div>
  );
}

function btn(c: Record<string, string>, bg?: string, fg?: string): React.CSSProperties {
  return {
    padding: "8px 12px",
    borderRadius: 8,
    border: bg ? "none" : `1px solid ${c.btnGhostBorder}`,
    background: bg ?? c.btnGhostBg,
    color: fg ?? c.text,
    fontWeight: 600,
    cursor: "pointer",
  };
}

export function usePlatformProjects(platform: string) {
  const [projects, setProjects] = useState<string[]>([]);
  useEffect(() => {
    void getPlatformProjects(platform)
      .then((r) => setProjects(r.projects))
      .catch(() => setProjects([]));
  }, [platform]);
  return projects;
}
