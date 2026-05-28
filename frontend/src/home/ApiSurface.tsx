import React, { useEffect, useRef, useState } from "react";
import {
  createApiProject,
  executeApiRequest,
  exportApiLoadEvidence,
  exportApiRequestEvidence,
  getApiEnvironment,
  getApiEnvironments,
  getApiProjectConfig,
  getApiProjects,
  getApiScenarioDetail,
  getApiScenarios,
  getApiTrafficCaptures,
  getApiWebOrigin,
  getProjectReportUrl,
  getTestRun,
  importApiTrafficCapture,
  importOpenApiSpec,
  importPostmanCollection,
  runLoadTest,
  saveApiEnvironment,
  saveApiLoadSnapshot,
  saveApiProjectConfig,
  saveApiScenario,
  syncApiEnvironmentFromWeb,
} from "../api";
import {
  DataCsvPanel,
  LoadHistoryComparePanel,
  LoadMetricsPanel,
  SuiteRunnerPanel,
  type AssertionRow,
  type ExtractorRow,
} from "./ApiAdvancedPanels";
import { RunConsolePanel } from "./RunConsolePanel";
import { ApiPostmanSidebar } from "./api/ApiPostmanSidebar";
import { ApiPostmanWorkspace, type PostmanPane } from "./api/ApiPostmanWorkspace";
import { ApiSection, apiBtn, apiInputStyle } from "./api/apiUi";

type Props = {
  c: Record<string, string>;
  modules: { api_testing?: boolean; api_limits?: { max_load_users?: number; max_suite_scenarios?: number } } | null;
  canRunJobs: boolean;
  onShowError: (msg: string) => void;
  setHomeHint: (msg: string | null) => void;
};

type HeaderRow = { key: string; value: string };
type ExecResult = Awaited<ReturnType<typeof executeApiRequest>>;
type ApiSubTab = "postman" | "load";

const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"];

export function ApiSurface(props: Props) {
  const { c, modules, canRunJobs, onShowError, setHomeHint } = props;
  const [projects, setProjects] = useState<string[]>([]);
  const [project, setProject] = useState("DefaultApi");
  const [newProject, setNewProject] = useState("");
  const [scenarios, setScenarios] = useState<{ id: string; name: string }[]>([]);
  const [captures, setCaptures] = useState<{ id: string; name: string; path: string }[]>([]);
  const [environments, setEnvironments] = useState<string[]>(["dev"]);
  const [environment, setEnvironment] = useState("dev");
  const [envVarsText, setEnvVarsText] = useState('{\n  "base_url": "https://api.ejemplo.com"\n}');
  const [globalHeaders, setGlobalHeaders] = useState<HeaderRow[]>([{ key: "", value: "" }]);
  const [method, setMethod] = useState("GET");
  const [url, setUrl] = useState("{{base_url}}/recurso");
  const [body, setBody] = useState("");
  const [expectedStatus, setExpectedStatus] = useState("200");
  const [reqHeaders, setReqHeaders] = useState<HeaderRow[]>([{ key: "Content-Type", value: "application/json" }]);
  const [selectedScenarios, setSelectedScenarios] = useState<Record<string, boolean>>({});
  const [loadUsers, setLoadUsers] = useState("5");
  const [loadSpawn, setLoadSpawn] = useState("1");
  const [loadRunTime, setLoadRunTime] = useState("1m");
  const [loadHost, setLoadHost] = useState("");
  const [scenarioWeights, setScenarioWeights] = useState<Record<string, string>>({});
  const [assertions, setAssertions] = useState<AssertionRow[]>([]);
  const [extractors, setExtractors] = useState<ExtractorRow[]>([]);
  const [maxDurationMs, setMaxDurationMs] = useState("");
  const [requestWeight, setRequestWeight] = useState("1");
  const [generateLoadReport, setGenerateLoadReport] = useState(false);
  const [loadRunFinished, setLoadRunFinished] = useState(false);
  const [loadReportFilename, setLoadReportFilename] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [execResult, setExecResult] = useState<ExecResult | null>(null);
  const [busy, setBusy] = useState(false);
  const initialized = useRef(false);
  const [importKind, setImportKind] = useState<"postman" | "openapi">("postman");
  const [apiTab, setApiTab] = useState<ApiSubTab>("postman");
  const [postmanPane, setPostmanPane] = useState<PostmanPane>("request");
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [webOriginAvailable, setWebOriginAvailable] = useState(false);

  const refreshProjects = () => {
    void getApiProjects()
      .then((r) => setProjects(r.projects))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  const refreshScenarios = () => {
    if (!project.trim()) return;
    void getApiScenarios(project)
      .then((r) => {
        const list = r.scenarios.map((s) => ({ id: s.id, name: s.name }));
        setScenarios(list);
        setSelectedScenarios((prev) => {
          const next: Record<string, boolean> = {};
          for (const s of list) next[s.id] = prev[s.id] ?? true;
          return next;
        });
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  const refreshCaptures = () => {
    if (!project.trim()) return;
    void getApiTrafficCaptures(project)
      .then((r) => setCaptures(r.captures))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  const refreshConfig = () => {
    if (!project.trim()) return;
    void getApiProjectConfig(project)
      .then((cfg) => {
        setEnvironment(cfg.default_environment || "dev");
        const rows = Object.entries(cfg.global_headers || {}).map(([key, value]) => ({ key, value }));
        setGlobalHeaders(rows.length ? rows : [{ key: "", value: "" }]);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
    void getApiEnvironments(project)
      .then((r) => setEnvironments(r.environments.length ? r.environments : ["dev"]))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  const loadEnvironmentVars = (envName: string) => {
    void getApiEnvironment(project, envName)
      .then((env) => {
        setEnvVarsText(JSON.stringify(env.variables || {}, null, 2));
      })
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
    refreshConfig();
  }, [project]);

  useEffect(() => {
    if (project && environment) loadEnvironmentVars(environment);
    void getApiWebOrigin(project)
      .then((r) => setWebOriginAvailable(r.available))
      .catch(() => setWebOriginAvailable(false));
  }, [project, environment]);

  useEffect(() => {
    if (!runId) {
      setLoadRunFinished(false);
      return;
    }
    let cancelled = false;
    const poll = () => {
      void getTestRun(runId).then((run) => {
        if (cancelled) return;
        if (run.state === "done" || run.state === "error") {
          setLoadRunFinished(true);
          return;
        }
        window.setTimeout(poll, 1200);
      });
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    if (!runId || !loadRunFinished) return;
    const ids = scenarios.filter((s) => selectedScenarios[s.id]).map((s) => s.id);
    void saveApiLoadSnapshot({
      project,
      run_id: runId,
      users: Number(loadUsers) || 5,
      run_time: loadRunTime.trim() || "1m",
      host: loadHost.trim(),
      scenario_count: ids.length,
    })
      .then(() => setHistoryRefresh((n) => n + 1))
      .catch(() => undefined);
  }, [loadRunFinished, runId]);

  if (!modules?.api_testing) {
    return (
      <div style={{ fontSize: 14, color: c.muted }}>
        El módulo de pruebas API requiere licencia vigente con <b>api_testing</b> habilitado.
      </div>
    );
  }

  const headersToRecord = (rows: HeaderRow[]) =>
    Object.fromEntries(rows.filter((r) => r.key.trim()).map((r) => [r.key.trim(), r.value]));

  const buildRequestPayload = () => ({
    id: `manual-${Date.now()}`,
    name: `${method} ${url.split("?")[0].slice(-40)}`,
    method,
    url: url.trim(),
    body: body.trim() || null,
    expected_status: Number(expectedStatus) || 200,
    headers: headersToRecord(reqHeaders),
    assertions: assertions.filter((a) => a.kind).map((a) => ({ kind: a.kind, expression: a.expression, expected: a.expected })),
    extractors: extractors.filter((e) => e.target_var.trim()).map((e) => ({ kind: e.kind, expression: e.expression, target_var: e.target_var })),
    max_duration_ms: maxDurationMs.trim() ? Number(maxDurationMs) : null,
    weight: Number(requestWeight) || 1,
    source: "manual",
  });

  const handleSend = () => {
    if (!url.trim()) {
      onShowError("URL requerida.");
      return;
    }
    setBusy(true);
    setExecResult(null);
    void executeApiRequest({ project, environment, request: buildRequestPayload() })
      .then((r) => setExecResult(r))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleSaveScenario = () => {
    if (!url.trim()) {
      onShowError("URL requerida para guardar escenario API.");
      return;
    }
    setBusy(true);
    void saveApiScenario({ project, scenario: buildRequestPayload() })
      .then(() => {
        refreshScenarios();
        setHomeHint("Escenario API guardado.");
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleSaveGlobalConfig = () => {
    setBusy(true);
    void saveApiProjectConfig(project, {
      default_environment: environment,
      global_headers: headersToRecord(globalHeaders),
    })
      .then(() => setHomeHint("Configuración del proyecto guardada."))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleSaveEnvironment = () => {
    let variables: Record<string, string>;
    try {
      const parsed = JSON.parse(envVarsText);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("El entorno debe ser un objeto JSON");
      }
      variables = Object.fromEntries(Object.entries(parsed).map(([k, v]) => [k, String(v)]));
    } catch (e: unknown) {
      onShowError(`Variables de entorno inválidas: ${String((e as Error)?.message ?? e)}`);
      return;
    }
    setBusy(true);
    void saveApiEnvironment(project, environment, { name: environment, variables })
      .then(() => setHomeHint(`Entorno ${environment} guardado.`))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleImportCapture = (captureId: string) => {
    setBusy(true);
    void importApiTrafficCapture(project, captureId)
      .then((r) => {
        refreshScenarios();
        const skipped = r.skipped ? ` (${r.skipped} duplicados omitidos)` : "";
        setHomeHint(`${r.imported ?? r.count} escenario(s) importado(s)${skipped}.`);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleSyncFromWeb = () => {
    setBusy(true);
    void syncApiEnvironmentFromWeb(project, environment)
      .then((r) => {
        loadEnvironmentVars(environment);
        setHomeHint(`base_url sincronizado desde web: ${r.base_url}`);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleLoadScenario = (scenarioId: string) => {
    setBusy(true);
    void getApiScenarioDetail(project, scenarioId)
      .then((r) => {
        const s = r.scenario;
        setMethod(String(s.method || "GET"));
        setUrl(String(s.url || ""));
        setBody(String(s.body || ""));
        setExpectedStatus(String(s.expected_status || 200));
        const hdrs = Object.entries((s.headers as Record<string, string>) || {}).map(([key, value]) => ({
          key,
          value,
        }));
        setReqHeaders(hdrs.length ? hdrs : [{ key: "", value: "" }]);
        const rawAssertions = (s.assertions as Array<{ kind: string; expression?: string; expected?: string }>) || [];
        setAssertions(
          rawAssertions.length
            ? rawAssertions.map((a) => ({ kind: a.kind, expression: a.expression || "", expected: a.expected || "" }))
            : [],
        );
        const rawExtractors = (s.extractors as Array<{ kind: string; expression?: string; target_var?: string }>) || [];
        setExtractors(
          rawExtractors.length
            ? rawExtractors.map((e) => ({ kind: e.kind, expression: e.expression || "", target_var: e.target_var || "" }))
            : [],
        );
        setMaxDurationMs(s.max_duration_ms != null ? String(s.max_duration_ms) : "");
        setRequestWeight(String(s.weight || 1));
        setApiTab("postman");
        setPostmanPane("request");
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleImportFile = (file: File) => {
    setBusy(true);
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result || "{}"));
        const task =
          importKind === "postman"
            ? importPostmanCollection({ project, collection: parsed })
            : importOpenApiSpec({ project, spec: parsed });
        void task
          .then((r) => {
            refreshScenarios();
            setHomeHint(`${r.count} escenario(s) importado(s).`);
          })
          .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
          .finally(() => setBusy(false));
      } catch (e: unknown) {
        setBusy(false);
        onShowError(`JSON inválido: ${String((e as Error)?.message ?? e)}`);
      }
    };
    reader.readAsText(file);
  };

  const handleExportEvidence = (format: "pdf" | "json") => {
    if (!execResult) return;
    setBusy(true);
    void exportApiRequestEvidence({
      project,
      environment,
      request: buildRequestPayload(),
      result: execResult,
      format,
    })
      .then((r) => {
        if (format === "pdf") {
          window.open(getProjectReportUrl("api", project, r.filename), "_blank");
        }
        setHomeHint(`Evidencia ${format.toUpperCase()} guardada: ${r.filename}`);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleExportLoadReport = (format: "pdf" | "html" = "pdf") => {
    if (!runId) return;
    const ids = scenarios.filter((s) => selectedScenarios[s.id]).map((s) => s.id);
    setBusy(true);
    void exportApiLoadEvidence({
      project,
      run_id: runId,
      users: Number(loadUsers) || 5,
      run_time: loadRunTime.trim() || "1m",
      host: loadHost.trim(),
      scenario_count: ids.length,
      format,
      enriched: true,
    })
      .then((r) => {
        setLoadReportFilename(r.filename);
        window.open(getProjectReportUrl("api", project, r.filename), "_blank");
        setHomeHint(`Reporte de carga (${format.toUpperCase()}) generado: ${r.filename}`);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleRunLocust = () => {
    const ids = scenarios.filter((s) => selectedScenarios[s.id]).map((s) => s.id);
    if (!ids.length) {
      onShowError("Selecciona al menos un escenario para Locust.");
      return;
    }
    setBusy(true);
    setLoadRunFinished(false);
    setLoadReportFilename(null);
    void runLoadTest({
      project,
      users: Number(loadUsers) || 5,
      spawn_rate: Number(loadSpawn) || 1,
      run_time: loadRunTime.trim() || "1m",
      host: loadHost.trim(),
      scenario_ids: ids,
      scenario_weights: Object.fromEntries(
        ids.map((id) => [id, Number(scenarioWeights[id]) || 1]),
      ),
      collect_metrics: true,
    })
      .then((r) => setRunId(r.run_id))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  return (
    <div data-testid="elia-api-panel">
      <div style={{ fontSize: 14, marginBottom: 12, color: c.text }}>
        Pruebas API: constructor estilo Postman y pruebas de carga JMeter-lite con Locust.
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14, alignItems: "center" }}>
        <label style={{ fontSize: 13, color: c.muted }}>Proyecto</label>
        <select
          value={project}
          onChange={(e) => setProject(e.target.value)}
          style={apiInputStyle(c, { minWidth: 140 })}
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
          style={apiInputStyle(c, { minWidth: 160 })}
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
          style={apiBtn(c)}
        >
          Crear
        </button>
        <label style={{ fontSize: 13, color: c.muted }}>Entorno</label>
        <select
          value={environment}
          onChange={(e) => setEnvironment(e.target.value)}
          style={apiInputStyle(c, { minWidth: 100 })}
        >
          {environments.map((env) => (
            <option key={env} value={env}>
              {env}
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        {(
          [
            { id: "postman" as const, label: "Postman" },
            { id: "load" as const, label: "JMeter-lite / Locust" },
          ] as const
        ).map(({ id, label }) => {
          const active = apiTab === id;
          return (
            <button
              key={id}
              type="button"
              data-testid={`elia-api-subtab-${id}`}
              onClick={() => setApiTab(id)}
              style={{
                padding: "7px 18px",
                borderRadius: 8,
                border: active ? `2px solid ${c.primary}` : `1px solid ${c.btnGhostBorder}`,
                background: active ? c.primary : c.btnGhostBg,
                color: active ? c.primaryFg : c.text,
                fontWeight: active ? 700 : 400,
                cursor: "pointer",
                fontSize: 14,
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      {apiTab === "postman" ? (
        <div
          data-testid="elia-api-postman-layout"
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(220px, 28%) 1fr",
            gap: 14,
            alignItems: "start",
          }}
        >
          <ApiPostmanSidebar
            c={c}
            busy={busy}
            canRunJobs={canRunJobs}
            scenarios={scenarios}
            captures={captures}
            importKind={importKind}
            onImportKindChange={setImportKind}
            onImportFile={handleImportFile}
            onImportCapture={handleImportCapture}
            onLoadScenario={handleLoadScenario}
          />
          <ApiPostmanWorkspace
            c={c}
            busy={busy}
            canRunJobs={canRunJobs}
            pane={postmanPane}
            onPaneChange={setPostmanPane}
            envVarsText={envVarsText}
            onEnvVarsTextChange={setEnvVarsText}
            globalHeaders={globalHeaders}
            onGlobalHeadersChange={setGlobalHeaders}
            webOriginAvailable={webOriginAvailable}
            onSaveEnvironment={handleSaveEnvironment}
            onSaveGlobalConfig={handleSaveGlobalConfig}
            onSyncFromWeb={handleSyncFromWeb}
            method={method}
            methods={METHODS}
            onMethodChange={setMethod}
            url={url}
            onUrlChange={setUrl}
            expectedStatus={expectedStatus}
            onExpectedStatusChange={setExpectedStatus}
            reqHeaders={reqHeaders}
            onReqHeadersChange={setReqHeaders}
            maxDurationMs={maxDurationMs}
            onMaxDurationMsChange={setMaxDurationMs}
            assertions={assertions}
            onAssertionsChange={setAssertions}
            extractors={extractors}
            onExtractorsChange={setExtractors}
            body={body}
            onBodyChange={setBody}
            onSend={handleSend}
            onSaveScenario={handleSaveScenario}
            execResult={execResult}
            onExportEvidence={handleExportEvidence}
          />
        </div>
      ) : (
        <>
      <ApiSection c={c} title="Datos CSV (data-driven)">
        <DataCsvPanel c={c} project={project} busy={busy} onError={onShowError} onHint={setHomeHint} />
      </ApiSection>

      <ApiSection c={c} title={`Escenarios para carga (${scenarios.length})`}>
        {scenarios.length === 0 ? (
          <div style={{ fontSize: 13, color: c.muted }}>Sin escenarios guardados.</div>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none", fontSize: 13 }}>
            {scenarios.map((s) => (
              <li
                key={s.id}
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                  marginBottom: 8,
                  flexWrap: "wrap",
                }}
              >
                <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <input
                    type="checkbox"
                    checked={!!selectedScenarios[s.id]}
                    onChange={(e) =>
                      setSelectedScenarios((prev) => ({ ...prev, [s.id]: e.target.checked }))
                    }
                  />
                  {s.name}
                </label>
                <input
                  type="number"
                  min={1}
                  value={scenarioWeights[s.id] ?? "1"}
                  onChange={(e) => setScenarioWeights((prev) => ({ ...prev, [s.id]: e.target.value }))}
                  title="Peso Locust"
                  style={{ ...apiInputStyle(c, { width: 56 }), padding: "4px 6px" }}
                />
                <button type="button" disabled={busy} onClick={() => handleLoadScenario(s.id)} style={apiBtn(c)}>
                  Cargar
                </button>
              </li>
            ))}
          </ul>
        )}
      </ApiSection>

      <ApiSection c={c} title="Suite funcional">
        <SuiteRunnerPanel
          c={c}
          project={project}
          environment={environment}
          scenarioIds={scenarios.filter((s) => selectedScenarios[s.id]).map((s) => s.id)}
          canRun={canRunJobs}
          busy={busy}
          onError={onShowError}
          onHint={setHomeHint}
        />
      </ApiSection>

      <ApiSection c={c} title="Prueba de carga (Locust)">
        <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>
          Métricas en RAM/consola. CSV Locust opt-in automático para dashboard. PDF/HTML solo bajo demanda.
          {modules?.api_limits?.max_load_users ? (
            <> Límite licencia: {modules.api_limits.max_load_users} usuarios.</>
          ) : null}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 10 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Usuarios</label>
            <input
              value={loadUsers}
              onChange={(e) => setLoadUsers(e.target.value)}
              style={apiInputStyle(c, { width: 80 })}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Tasa de subida</label>
            <input
              value={loadSpawn}
              onChange={(e) => setLoadSpawn(e.target.value)}
              style={apiInputStyle(c, { width: 80 })}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Duración</label>
            <input
              value={loadRunTime}
              onChange={(e) => setLoadRunTime(e.target.value)}
              placeholder="1m"
              style={apiInputStyle(c, { width: 72 })}
            />
          </div>
          <div style={{ flex: "1 1 200px" }}>
            <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Host base (opcional)</label>
            <input
              value={loadHost}
              onChange={(e) => setLoadHost(e.target.value)}
              placeholder="https://api.ejemplo.com"
              style={apiInputStyle(c, { width: "100%" })}
            />
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={generateLoadReport}
              onChange={(e) => setGenerateLoadReport(e.target.checked)}
            />
            Permitir reporte PDF al finalizar
          </label>
          <button type="button" disabled={!canRunJobs || busy} onClick={handleRunLocust} style={apiBtn(c, c.primary, c.primaryFg)}>
            Ejecutar Locust
          </button>
        </div>
        {loadRunFinished && generateLoadReport ? (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
            <button type="button" disabled={busy} onClick={() => handleExportLoadReport("pdf")} style={apiBtn(c, c.primary, c.primaryFg)}>
              Generar reporte enriquecido (PDF)
            </button>
            <button type="button" disabled={busy} onClick={() => handleExportLoadReport("html")} style={apiBtn(c, undefined, undefined, true)}>
              Generar reporte enriquecido (HTML)
            </button>
            {loadReportFilename ? (
              <span style={{ fontSize: 12, color: c.muted }}>Guardado: {loadReportFilename}</span>
            ) : null}
          </div>
        ) : null}
        <LoadMetricsPanel c={c} runId={runId} />
        <LoadHistoryComparePanel c={c} project={project} refreshToken={historyRefresh} onError={onShowError} />
        {runId ? (
          <div style={{ marginTop: 12 }}>
            <RunConsolePanel
              c={c}
              runId={runId}
              platform="api"
              project={project}
              onClose={() => setRunId(null)}
            />
          </div>
        ) : null}
      </ApiSection>
        </>
      )}
    </div>
  );
}
