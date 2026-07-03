import React, { useEffect, useMemo, useState } from "react";
import {
  getPlatformProjects,
  listProjectFiles,
  readProjectFile,
  startUnifiedRun,
  writeProjectFile,
} from "../api";
import { FileTree } from "../components/FileTree";
import { EliaButton, FieldLabel } from "../components/ui";
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
  const [showBrowser, setShowBrowser] = useState(false);
  const [loadUsers, setLoadUsers] = useState("5");
  const [fullscreen, setFullscreen] = useState(false);
  const [showAdvancedFiles, setShowAdvancedFiles] = useState(false);
  const [acRefresh, setAcRefresh] = useState(0);
  const autocompleteContext = useProjectAutocomplete(platform, project, files, acRefresh);
  const liveAutocomplete = useMemo(
    () => patchContextWithEditor(autocompleteContext, selected, editor),
    [autocompleteContext, selected, editor],
  );

  useEffect(() => {
    setFiles([]);
    setSelected("");
    setEditor("");
    setDirty(false);
    setRunId(null);
  }, [platform, project]);

  useEffect(() => {
    if (!project.trim()) {
      setFiles([]);
      return;
    }

    let cancelled = false;
    void listProjectFiles(platform, project, showAdvancedFiles)
      .then((r) => {
        if (!cancelled) setFiles(r.files);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setFiles([]);
        const msg = String((e as Error)?.message ?? e);
        if (!msg.includes("404")) {
          onShowError(msg);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [platform, project, showAdvancedFiles, onShowError]);

  const refreshFiles = () => {
    if (!project.trim()) {
      setFiles([]);
      return;
    }
    void listProjectFiles(platform, project, showAdvancedFiles)
      .then((r) => setFiles(r.files))
      .catch((e: unknown) => {
        setFiles([]);
        const msg = String((e as Error)?.message ?? e);
        if (!msg.includes("404")) {
          onShowError(msg);
        }
      });
  };

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
      headless: !showBrowser,
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
      <EliaButton variant="ghost" size="sm" disabled={!selected || !dirty || busy} onClick={saveFile}>
        Guardar
      </EliaButton>
      <EliaButton variant="ghost" size="sm" disabled={!selected || busy} onClick={() => loadFile(selected)}>
        Recargar
      </EliaButton>
      <EliaButton
        variant="ghost"
        size="icon"
        title={fullscreen ? "Salir de pantalla completa" : "Pantalla completa"}
        onClick={() => setFullscreen((v) => !v)}
      >
        {fullscreen ? "🡷" : "🡵"}
      </EliaButton>
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
      <FieldLabel
        c={c}
        tooltip={
          <>
            Qué ejecutará Behave: «features» corre todos los .feature; «features/mi.feature» solo uno. Este campo filtra
            la ejecución; el editor de abajo sirve para editar archivos.
            {platform === "web"
              ? " Por defecto Chrome corre headless; marca «Mostrar navegador» para ver la UI."
              : null}
          </>
        }
        style={{ marginBottom: 6 }}
      >
        Filtro de ejecución Behave
      </FieldLabel>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10, alignItems: "center" }}>
        <input
          className="elia-input"
          value={featureFile}
          onChange={(e) => setFeatureFile(e.target.value)}
          placeholder="features o features/mi.feature"
          style={{ flex: "1 1 200px" }}
        />
        <EliaButton variant="primary" size="sm" disabled={!canRunJobs || busy} onClick={runBehave}>
          Ejecutar Behave
        </EliaButton>
        {platform === "web" ? (
          <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
            <input
              type="checkbox"
              checked={showBrowser}
              onChange={(e) => setShowBrowser(e.target.checked)}
            />
            Mostrar navegador
          </label>
        ) : null}
        {showLocust ? (
          <>
            <input
              className="elia-input"
              value={loadUsers}
              onChange={(e) => setLoadUsers(e.target.value)}
              style={{ width: 70 }}
            />
            <EliaButton variant="ghost" size="sm" disabled={!canRunJobs || busy} onClick={runLocust}>
              Ejecutar Locust
            </EliaButton>
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
            display: "flex",
            flexDirection: "column",
          }}
        >
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 10px",
              borderBottom: `1px solid ${c.border}`,
              fontSize: 11,
              color: c.muted,
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={showAdvancedFiles}
              onChange={(e) => setShowAdvancedFiles(e.target.checked)}
            />
            Código avanzado (button_functions.py)
          </label>
          <div style={{ flex: 1, overflow: "auto" }}>
            {files.length === 0 ? (
              <div style={{ padding: 10, color: c.muted }}>Sin archivos editables</div>
            ) : (
              <FileTree c={c} files={files} selectedPath={selected} onSelectFile={loadFile} />
            )}
          </div>
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

export function usePlatformProjects(platform: string, refreshKey = 0) {
  const [projects, setProjects] = useState<string[]>([]);
  useEffect(() => {
    let cancelled = false;
    void getPlatformProjects(platform)
      .then((r) => {
        if (!cancelled) setProjects(r.projects);
      })
      .catch(() => {
        if (!cancelled) setProjects([]);
      });
    return () => {
      cancelled = true;
    };
  }, [platform, refreshKey]);
  return projects;
}
