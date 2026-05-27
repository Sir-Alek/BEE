import React, { useEffect, useRef, useState } from "react";
import {
  convertApiScenarios,
  createApiProject,
  getApiProjects,
  getApiScenarios,
  getApiTrafficCaptures,
  importApiTrafficCapture,
  runLoadTest,
  saveApiScenario,
  startTestRun,
} from "../api";
import { RunConsolePanel } from "./RunConsolePanel";

type Props = {
  c: Record<string, string>;
  modules: { api_testing?: boolean } | null;
  canRunJobs: boolean;
  onShowError: (msg: string) => void;
  setHomeHint: (msg: string | null) => void;
};

export function ApiSurface(props: Props) {
  const { c, modules, canRunJobs, onShowError, setHomeHint } = props;
  const [projects, setProjects] = useState<string[]>([]);
  const [project, setProject] = useState("DefaultApi");
  const [newProject, setNewProject] = useState("");
  const [scenarios, setScenarios] = useState<{ id: string; name: string }[]>([]);
  const [captures, setCaptures] = useState<{ id: string; name: string; path: string }[]>([]);
  const [method, setMethod] = useState("GET");
  const [url, setUrl] = useState("");
  const [body, setBody] = useState("");
  const [expectedStatus, setExpectedStatus] = useState("200");
  const [runId, setRunId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadUsers, setLoadUsers] = useState("5");
  const initialized = useRef(false);

  const refreshProjects = () => {
    void getApiProjects()
      .then((r) => setProjects(r.projects))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  const refreshScenarios = () => {
    if (!project.trim()) return;
    void getApiScenarios(project)
      .then((r) => setScenarios(r.scenarios.map((s) => ({ id: s.id, name: s.name }))))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  const refreshCaptures = () => {
    if (!project.trim()) return;
    void getApiTrafficCaptures(project)
      .then((r) => setCaptures(r.captures))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      refreshProjects();
    }
  }, []);

  useEffect(() => {
    refreshScenarios();
    refreshCaptures();
  }, [project]);

  if (!modules?.api_testing) {
    return (
      <div style={{ fontSize: 14, color: c.muted }}>
        El módulo de pruebas API requiere licencia vigente con <b>api_testing</b> habilitado.
      </div>
    );
  }

  const handleSaveScenario = () => {
    if (!url.trim()) {
      onShowError("URL requerida para guardar escenario API.");
      return;
    }
    setBusy(true);
    void saveApiScenario({
      project,
      scenario: {
        id: `manual-${Date.now()}`,
        name: `${method} ${url.split("?")[0].slice(-40)}`,
        method,
        url: url.trim(),
        body: body.trim() || null,
        expected_status: Number(expectedStatus) || 200,
        headers: {},
        source: "manual",
      },
    })
      .then(() => refreshScenarios())
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleImportCapture = (captureId: string) => {
    setBusy(true);
    void importApiTrafficCapture(project, captureId)
      .then((r) => {
        refreshScenarios();
        setHomeHint(`${r.count} escenario(s) importado(s) desde la captura web.`);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleConvertCapture = (capturePath: string, captureName: string) => {
    setBusy(true);
    void convertApiScenarios({ project, traffic_path: capturePath, feature_name: captureName })
      .then(() => setHomeHint("Feature Behave API generado desde captura web."))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleConvert = () => {
    setBusy(true);
    void convertApiScenarios({ project, scenario_ids: scenarios.map((s) => s.id) })
      .then(() => setHomeHint("Feature Behave API generado correctamente."))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleRunBehave = () => {
    setBusy(true);
    void startTestRun({ project, kind: "behave_api" })
      .then((r) => setRunId(r.run_id))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleLoadTest = () => {
    setBusy(true);
    void runLoadTest({
      project,
      users: Number(loadUsers) || 5,
      spawn_rate: 1,
      run_time: "1m",
      host: url.startsWith("http") ? new URL(url).origin : "",
    })
      .then((r) => setRunId(r.run_id))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  return (
    <div data-testid="elia-api-panel">
      <div style={{ fontSize: 14, marginBottom: 12, color: c.text }}>
        Pruebas API estilo JMeter/Postman: captura tráfico web, escenarios manuales, Behave HTTP y Locust.
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12, alignItems: "center" }}>
        <label style={{ fontSize: 13, color: c.muted }}>Proyecto</label>
        <select
          value={project}
          onChange={(e) => setProject(e.target.value)}
          style={{
            padding: "8px 10px",
            borderRadius: 8,
            border: `1px solid ${c.inputBorder}`,
            background: c.inputBg,
            color: c.text,
          }}
        >
          {[...new Set([project, ...projects])].map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <input
          value={newProject}
          onChange={(e) => setNewProject(e.target.value)}
          placeholder="Nuevo proyecto"
          style={{
            padding: "8px 10px",
            borderRadius: 8,
            border: `1px solid ${c.inputBorder}`,
            background: c.inputBg,
            color: c.text,
            minWidth: 160,
          }}
        />
        <button
          type="button"
          disabled={!newProject.trim() || busy}
          onClick={() => {
            void createApiProject(newProject.trim()).then(() => {
              setProject(newProject.trim());
              setNewProject("");
              refreshProjects();
            });
          }}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: `1px solid ${c.btnGhostBorder}`,
            background: c.btnGhostBg,
            cursor: "pointer",
          }}
        >
          Crear
        </button>
      </div>

      <div
        style={{
          border: `1px solid ${c.border}`,
          borderRadius: 12,
          padding: 14,
          marginBottom: 14,
          background: c.neutralBg,
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 10 }}>Constructor manual (Postman-lite)</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            style={{ padding: "8px 10px", borderRadius: 8, border: `1px solid ${c.inputBorder}` }}
          >
            {["GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://api.ejemplo.com/recurso"
            style={{
              flex: "1 1 280px",
              padding: "8px 10px",
              borderRadius: 8,
              border: `1px solid ${c.inputBorder}`,
              background: c.inputBg,
              color: c.text,
            }}
          />
          <input
            value={expectedStatus}
            onChange={(e) => setExpectedStatus(e.target.value)}
            placeholder="200"
            style={{
              width: 72,
              padding: "8px 10px",
              borderRadius: 8,
              border: `1px solid ${c.inputBorder}`,
            }}
          />
        </div>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder='Body JSON (opcional)'
          rows={4}
          style={{
            width: "100%",
            boxSizing: "border-box",
            padding: "10px 12px",
            borderRadius: 10,
            border: `1px solid ${c.inputBorder}`,
            background: c.inputBg,
            color: c.text,
            fontFamily: "monospace",
            fontSize: 13,
            marginBottom: 10,
          }}
        />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" disabled={!canRunJobs || busy} onClick={handleSaveScenario} style={btn(c, c.primary, c.primaryFg)}>
            Guardar escenario
          </button>
          <button type="button" disabled={!canRunJobs || busy || scenarios.length === 0} onClick={handleConvert} style={btn(c)}>
            Generar .feature Behave
          </button>
          <button type="button" disabled={!canRunJobs || busy} onClick={handleRunBehave} style={btn(c)}>
            Ejecutar Behave API
          </button>
        </div>
      </div>

      <div
        style={{
          border: `1px solid ${c.border}`,
          borderRadius: 12,
          padding: 14,
          marginBottom: 14,
          background: c.surface,
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Capturas desde grabación web</div>
        <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>
          Si grabaste con «Capturar tráfico API», los JSON quedan en{" "}
          <code style={{ fontSize: 12 }}>behave/api/&lt;proyecto&gt;/scripts/</code> (mismo nombre que el proyecto web).
        </div>
        {captures.length === 0 ? (
          <div style={{ fontSize: 13, color: c.muted }}>Sin capturas en este proyecto API.</div>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
            {captures.map((cap) => (
              <li key={cap.id} style={{ marginBottom: 8 }}>
                <span>{cap.name}</span>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 6 }}>
                  <button
                    type="button"
                    disabled={!canRunJobs || busy}
                    onClick={() => handleImportCapture(cap.id)}
                    style={btn(c)}
                  >
                    Importar a escenarios
                  </button>
                  <button
                    type="button"
                    disabled={!canRunJobs || busy}
                    onClick={() => handleConvertCapture(cap.path, cap.name)}
                    style={btn(c)}
                  >
                    Generar .feature Behave
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ marginBottom: 12, fontSize: 13, color: c.muted }}>
        Escenarios guardados: {scenarios.length}
        {scenarios.length > 0 ? (
          <ul style={{ margin: "8px 0 0 0", paddingLeft: 18 }}>
            {scenarios.slice(0, 8).map((s) => (
              <li key={s.id}>{s.name}</li>
            ))}
          </ul>
        ) : null}
      </div>

      <div
        style={{
          border: `1px solid ${c.border}`,
          borderRadius: 12,
          padding: 14,
          marginBottom: 14,
          background: c.surface,
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Prueba de carga (Locust)</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <input
            value={loadUsers}
            onChange={(e) => setLoadUsers(e.target.value)}
            placeholder="Usuarios"
            style={{ width: 90, padding: "8px 10px", borderRadius: 8, border: `1px solid ${c.inputBorder}` }}
          />
          <button type="button" disabled={!canRunJobs || busy || scenarios.length === 0} onClick={handleLoadTest} style={btn(c)}>
            Ejecutar Locust
          </button>
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
