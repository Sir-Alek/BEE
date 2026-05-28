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
  AssertionEditor,
  DataCsvPanel,
  ExtractorEditor,
  LoadHistoryComparePanel,
  LoadMetricsPanel,
  SuiteRunnerPanel,
  type AssertionRow,
  type ExtractorRow,
} from "./ApiAdvancedPanels";
import { RunConsolePanel } from "./RunConsolePanel";

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
  const importRef = useRef<HTMLInputElement>(null);
  const [importKind, setImportKind] = useState<"postman" | "openapi">("postman");
  const [apiTab, setApiTab] = useState<ApiSubTab>("postman");
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
          style={inputStyle(c, { minWidth: 140 })}
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
          style={inputStyle(c, { minWidth: 160 })}
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
          style={btn(c)}
        >
          Crear
        </button>
        <label style={{ fontSize: 13, color: c.muted }}>Entorno</label>
        <select
          value={environment}
          onChange={(e) => setEnvironment(e.target.value)}
          style={inputStyle(c, { minWidth: 100 })}
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
        <>
      <Section c={c} title="Entorno y headers globales">
        <div style={{ fontSize: 13, color: c.muted, marginBottom: 8 }}>
          Usa <code style={{ fontSize: 12 }}>{"{{variable}}"}</code> en URL, headers y body. Se resuelven desde el entorno activo.
        </div>
        <textarea
          value={envVarsText}
          onChange={(e) => setEnvVarsText(e.target.value)}
          rows={4}
          style={monoArea(c)}
          placeholder='{"base_url": "https://api.ejemplo.com"}'
        />
        <HeaderEditor c={c} rows={globalHeaders} onChange={setGlobalHeaders} label="Headers globales" />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
          <button type="button" disabled={busy} onClick={handleSaveEnvironment} style={btn(c)}>
            Guardar entorno
          </button>
          <button type="button" disabled={busy} onClick={handleSaveGlobalConfig} style={btn(c)}>
            Guardar config proyecto
          </button>
          {webOriginAvailable ? (
            <button type="button" disabled={busy} onClick={handleSyncFromWeb} style={btn(c, undefined, undefined, true)}>
              Sincronizar base_url desde grabación web
            </button>
          ) : null}
        </div>
      </Section>

      <Section c={c} title="Petición HTTP">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            style={inputStyle(c, { width: 100 })}
          >
            {METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="{{base_url}}/recurso"
            style={inputStyle(c, { flex: "1 1 280px" })}
          />
          <input
            value={expectedStatus}
            onChange={(e) => setExpectedStatus(e.target.value)}
            placeholder="200"
            style={inputStyle(c, { width: 72 })}
          />
        </div>
        <HeaderEditor c={c} rows={reqHeaders} onChange={setReqHeaders} label="Headers de petición" />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          <input
            value={maxDurationMs}
            onChange={(e) => setMaxDurationMs(e.target.value)}
            placeholder="Max ms (opcional)"
            style={inputStyle(c, { width: 130 })}
          />
        </div>
        <AssertionEditor c={c} rows={assertions} onChange={setAssertions} />
        <ExtractorEditor c={c} rows={extractors} onChange={setExtractors} />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Body JSON (opcional)"
          rows={4}
          style={{ ...monoArea(c), marginTop: 8 }}
        />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
          <button type="button" disabled={!canRunJobs || busy} onClick={handleSend} style={btn(c, c.primary, c.primaryFg)}>
            Enviar
          </button>
          <button type="button" disabled={!canRunJobs || busy} onClick={handleSaveScenario} style={btn(c)}>
            Guardar escenario
          </button>
        </div>
        {execResult ? (
          <div
            style={{
              marginTop: 12,
              padding: 12,
              borderRadius: 10,
              border: `1px solid ${execResult.ok ? c.primary : "#c0392b"}`,
              background: c.surface,
              fontSize: 13,
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: 6 }}>
              {execResult.ok ? "OK" : "Falló"} — HTTP {execResult.status_code} ({execResult.elapsed_ms} ms)
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
              <button type="button" disabled={busy} onClick={() => handleExportEvidence("pdf")} style={btn(c)}>
                Exportar evidencia (PDF)
              </button>
              <button type="button" disabled={busy} onClick={() => handleExportEvidence("json")} style={btn(c)}>
                Exportar evidencia (JSON)
              </button>
            </div>
            {execResult.headers && Object.keys(execResult.headers).length > 0 ? (
              <details style={{ marginBottom: 8 }}>
                <summary style={{ cursor: "pointer", color: c.muted }}>Headers de respuesta</summary>
                <pre style={{ fontSize: 11, fontFamily: "monospace", whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(execResult.headers, null, 2)}
                </pre>
              </details>
            ) : null}
            {execResult.assertions?.length ? (
              <ul style={{ margin: "0 0 8px 0", paddingLeft: 18 }}>
                {execResult.assertions.map((a, i) => (
                  <li key={i} style={{ color: a.passed ? c.text : "#c0392b" }}>
                    {a.message}
                  </li>
                ))}
              </ul>
            ) : null}
            <pre
              style={{
                margin: 0,
                maxHeight: 220,
                overflow: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontSize: 12,
                fontFamily: "monospace",
              }}
            >
              {execResult.body?.slice(0, 8000) || "(sin cuerpo)"}
            </pre>
          </div>
        ) : null}
      </Section>

      <Section c={c} title="Importar colección">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select
            value={importKind}
            onChange={(e) => setImportKind(e.target.value as "postman" | "openapi")}
            style={inputStyle(c)}
          >
            <option value="postman">Postman v2.1</option>
            <option value="openapi">OpenAPI 3</option>
          </select>
          <input
            ref={importRef}
            type="file"
            accept=".json"
            style={{ display: "none" }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleImportFile(file);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            disabled={!canRunJobs || busy}
            onClick={() => importRef.current?.click()}
            style={btn(c)}
          >
            Importar JSON
          </button>
        </div>
      </Section>

      <Section c={c} title="Capturas desde grabación web">
        <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>
          JSON en <code style={{ fontSize: 12 }}>behave/api/&lt;proyecto&gt;/scripts/</code>
        </div>
        {captures.length === 0 ? (
          <div style={{ fontSize: 13, color: c.muted }}>Sin capturas en este proyecto API.</div>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
            {captures.map((cap) => (
              <li key={cap.id} style={{ marginBottom: 8 }}>
                <span>{cap.name}</span>
                <button
                  type="button"
                  disabled={!canRunJobs || busy}
                  onClick={() => handleImportCapture(cap.id)}
                  style={{ ...btn(c), marginLeft: 10 }}
                >
                  Importar a escenarios
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section c={c} title={`Escenarios guardados (${scenarios.length})`}>
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
                <span>{s.name}</span>
                <button type="button" disabled={busy} onClick={() => handleLoadScenario(s.id)} style={btn(c)}>
                  Cargar en constructor
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>
        </>
      ) : (
        <>
      <Section c={c} title="Datos CSV (data-driven)">
        <DataCsvPanel c={c} project={project} busy={busy} onError={onShowError} onHint={setHomeHint} />
      </Section>

      <Section c={c} title={`Escenarios para carga (${scenarios.length})`}>
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
                  style={{ ...inputStyle(c, { width: 56 }), padding: "4px 6px" }}
                />
                <button type="button" disabled={busy} onClick={() => handleLoadScenario(s.id)} style={btn(c)}>
                  Cargar
                </button>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section c={c} title="Suite funcional">
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
      </Section>

      <Section c={c} title="Prueba de carga (Locust)">
        <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>
          Métricas en RAM/consola. CSV Locust opt-in automático para dashboard. PDF/HTML solo bajo demanda.
          {modules?.api_limits?.max_load_users ? (
            <> Límite licencia: {modules.api_limits.max_load_users} usuarios.</>
          ) : null}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
          <input
            value={loadUsers}
            onChange={(e) => setLoadUsers(e.target.value)}
            placeholder="Usuarios"
            style={inputStyle(c, { width: 80 })}
          />
          <input
            value={loadSpawn}
            onChange={(e) => setLoadSpawn(e.target.value)}
            placeholder="Spawn/s"
            style={inputStyle(c, { width: 80 })}
          />
          <input
            value={loadRunTime}
            onChange={(e) => setLoadRunTime(e.target.value)}
            placeholder="1m"
            style={inputStyle(c, { width: 72 })}
          />
          <input
            value={loadHost}
            onChange={(e) => setLoadHost(e.target.value)}
            placeholder="Host base (opcional)"
            style={inputStyle(c, { flex: "1 1 200px" })}
          />
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={generateLoadReport}
              onChange={(e) => setGenerateLoadReport(e.target.checked)}
            />
            Permitir reporte PDF al finalizar
          </label>
          <button type="button" disabled={!canRunJobs || busy} onClick={handleRunLocust} style={btn(c, c.primary, c.primaryFg)}>
            Ejecutar Locust
          </button>
        </div>
        {loadRunFinished && generateLoadReport ? (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
            <button type="button" disabled={busy} onClick={() => handleExportLoadReport("pdf")} style={btn(c, c.primary, c.primaryFg)}>
              Generar reporte enriquecido (PDF)
            </button>
            <button type="button" disabled={busy} onClick={() => handleExportLoadReport("html")} style={btn(c, undefined, undefined, true)}>
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
      </Section>
        </>
      )}
    </div>
  );
}

function Section(props: { c: Record<string, string>; title: string; children: React.ReactNode }) {
  const { c, title, children } = props;
  return (
    <div
      style={{
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        padding: 14,
        marginBottom: 14,
        background: c.surface,
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );
}

function HeaderEditor(props: {
  c: Record<string, string>;
  rows: HeaderRow[];
  onChange: (rows: HeaderRow[]) => void;
  label: string;
}) {
  const { c, rows, onChange, label } = props;
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>{label}</div>
      {rows.map((row, idx) => (
        <div key={idx} style={{ display: "flex", gap: 8, marginBottom: 6, flexWrap: "wrap", alignItems: "center" }}>
          <input
            value={row.key}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], key: e.target.value };
              onChange(next);
            }}
            placeholder="Header"
            style={inputStyle(c, { flex: "1 1 140px" })}
          />
          <input
            value={row.value}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], value: e.target.value };
              onChange(next);
            }}
            placeholder="Valor"
            style={inputStyle(c, { flex: "2 1 200px" })}
          />
          <button
            type="button"
            title="Eliminar header"
            aria-label="Eliminar header"
            onClick={() => {
              const next = rows.filter((_, i) => i !== idx);
              onChange(next.length ? next : [{ key: "", value: "" }]);
            }}
            style={btn(c, undefined, undefined, true)}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...rows, { key: "", value: "" }])}
        style={btn(c, undefined, undefined, true)}
      >
        + Header
      </button>
    </div>
  );
}

function inputStyle(c: Record<string, string>, extra?: React.CSSProperties): React.CSSProperties {
  return {
    padding: "8px 10px",
    borderRadius: 8,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    ...extra,
  };
}

function monoArea(c: Record<string, string>): React.CSSProperties {
  return {
    width: "100%",
    boxSizing: "border-box",
    padding: "10px 12px",
    borderRadius: 10,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    fontFamily: "monospace",
    fontSize: 13,
  };
}

function btn(
  c: Record<string, string>,
  bg?: string,
  fg?: string,
  ghost?: boolean,
): React.CSSProperties {
  return {
    padding: "8px 12px",
    borderRadius: 8,
    border: bg || ghost ? (bg ? "none" : `1px solid ${c.btnGhostBorder}`) : `1px solid ${c.btnGhostBorder}`,
    background: bg ?? c.btnGhostBg,
    color: fg ?? c.text,
    fontWeight: 600,
    cursor: "pointer",
    fontSize: 13,
  };
}
