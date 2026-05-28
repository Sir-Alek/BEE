import React, { useEffect, useMemo, useState } from "react";
import {
  getPlatformProjects,
  listProjectFiles,
  readProjectFile,
  startUnifiedRun,
  writeProjectFile,
} from "../api";
import { useEliaTheme } from "../eliaTheme";
import { CodeEditorPanel } from "./CodeEditorPanel";
import { RunConsolePanel } from "./RunConsolePanel";
import { useProjectAutocomplete } from "./useProjectAutocomplete";
import { patchContextWithEditor } from "./editorAutocomplete";

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
  const { dark } = useEliaTheme();
  const [files, setFiles] = useState<{ path: string; name: string }[]>([]);
  const [selected, setSelected] = useState("");
  const [editor, setEditor] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [featureFile, setFeatureFile] = useState("features");
  const [loadUsers, setLoadUsers] = useState("5");
  const [fullscreen, setFullscreen] = useState(false);
  const [acRefresh, setAcRefresh] = useState(0);
  const autocompleteContext = useProjectAutocomplete(platform, project, files, acRefresh);
  const liveAutocomplete = useMemo(
    () => patchContextWithEditor(autocompleteContext, selected, editor),
    [autocompleteContext, selected, editor],
  );

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
        setAcRefresh((n) => n + 1);
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
      generate_evidence: true,
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

  const editorToolbar = (
    <>
      {dirty ? <span style={{ color: c.primary, fontSize: 11 }}>● Sin guardar</span> : null}
      <button type="button" disabled={!selected || !dirty || busy} onClick={saveFile} style={btn(c, undefined, undefined, true)}>
        Guardar
      </button>
      <button type="button" disabled={!selected || busy} onClick={() => loadFile(selected)} style={btn(c, undefined, undefined, true)}>
        Recargar
      </button>
      <button
        type="button"
        title={fullscreen ? "Salir de pantalla completa" : "Pantalla completa"}
        onClick={() => setFullscreen((v) => !v)}
        style={btn(c, undefined, undefined, true)}
      >
        {fullscreen ? "⤓" : "⤢"}
      </button>
    </>
  );

  const editorBlock = (
    <CodeEditorPanel
      value={editor}
      filePath={selected}
      dark={dark}
      readOnly={busy}
      minHeight={fullscreen ? "calc(100vh - 120px)" : "min(52vh, 520px)"}
      completionContext={liveAutocomplete}
      onChange={(v) => {
        setEditor(v);
        setDirty(true);
      }}
      onSave={saveFile}
      toolbar={editorToolbar}
    />
  );

  const workspaceBody = (
    <>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>Ejecutar y editar proyecto</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10, alignItems: "center" }}>
        <input
          value={featureFile}
          onChange={(e) => setFeatureFile(e.target.value)}
          placeholder="features o features/mi.feature"
          style={{ flex: "1 1 200px", padding: "8px 10px", borderRadius: 8, border: `1px solid ${c.inputBorder}` }}
        />
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

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(180px, 240px) 1fr",
          gap: 12,
          marginBottom: 12,
          minHeight: "min(52vh, 520px)",
        }}
      >
        <div
          style={{
            border: `1px solid ${c.border}`,
            borderRadius: 10,
            minHeight: "inherit",
            maxHeight: fullscreen ? "calc(100vh - 120px)" : "min(52vh, 520px)",
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
        <div style={{ minHeight: "inherit", display: "flex", flexDirection: "column" }}>
          {selected ? (
            editorBlock
          ) : (
            <div
              style={{
                flex: 1,
                border: `1px dashed ${c.border}`,
                borderRadius: 10,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: c.muted,
                fontSize: 13,
                minHeight: "min(52vh, 520px)",
              }}
            >
              Selecciona un .feature, .py o locustfile.py en el árbol de archivos
            </div>
          )}
        </div>
      </div>

      {runId ? (
        <RunConsolePanel
          c={c}
          runId={runId}
          platform={platform}
          project={project}
          onClose={() => setRunId(null)}
        />
      ) : null}
    </>
  );

  if (fullscreen) {
    return (
      <div
        data-testid="elia-run-workspace-fullscreen"
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 2000,
          background: c.pageBg,
          padding: 16,
          overflow: "auto",
        }}
      >
        {workspaceBody}
      </div>
    );
  }

  return (
    <div data-testid="elia-run-workspace" style={{ marginTop: 12 }}>
      {workspaceBody}
    </div>
  );
}

function btn(
  c: Record<string, string>,
  bg?: string,
  fg?: string,
  compact?: boolean,
): React.CSSProperties {
  return {
    padding: compact ? "4px 8px" : "8px 12px",
    borderRadius: 8,
    border: bg ? "none" : `1px solid ${c.btnGhostBorder}`,
    background: bg ?? c.btnGhostBg,
    color: fg ?? c.text,
    fontWeight: 600,
    cursor: "pointer",
    fontSize: compact ? 12 : 14,
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
