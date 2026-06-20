import React, { useEffect, useState } from "react";
import {
  compareApiLoadRuns,
  exportApiSuiteEvidence,
  getApiDataFiles,
  getApiDriverCapabilities,
  getApiFlow,
  getApiLoadHistory,
  getLoadTestMetrics,
  getProjectReportUrl,
  getTestRun,
  listApiFlows,
  runApiSuite,
  saveApiDataFile,
  saveApiFlow,
  sqlPreflight,
} from "../api";
import {
  NodeListEditor,
  deserializeFlowNodes,
  serializeFlowNodes,
  type DriverCapabilities,
  type FlowNode,
  type SqlConfig,
} from "./api/FlowControllerEditor";

export type KVRow = { key: string; value: string };
export type AssertionRow = { kind: string; expression: string; expected: string };
export type ExtractorRow = { kind: string; expression: string; target_var: string };

type Theme = Record<string, string>;

export function AssertionEditor(props: {
  c: Theme;
  rows: AssertionRow[];
  onChange: (rows: AssertionRow[]) => void;
}) {
  const { c, rows, onChange } = props;
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>Aserciones avanzadas</div>
      {rows.map((row, idx) => (
        <div key={idx} style={{ display: "flex", gap: 6, marginBottom: 6, flexWrap: "wrap", alignItems: "center" }}>
          <select
            value={row.kind}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], kind: e.target.value };
              onChange(next);
            }}
            style={inputStyle(c, { width: 110 })}
          >
            {["status", "jsonpath", "header", "duration", "regex", "body_contains"].map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
          <input
            value={row.expression}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], expression: e.target.value };
              onChange(next);
            }}
            placeholder="Expresión / header / JSONPath"
            style={inputStyle(c, { flex: "1 1 140px" })}
          />
          <input
            value={row.expected}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], expected: e.target.value };
              onChange(next);
            }}
            placeholder="Esperado"
            style={inputStyle(c, { flex: "1 1 100px" })}
          />
          <button type="button" onClick={() => onChange(rows.filter((_, i) => i !== idx))} style={btn(c, true)}>
            ✕
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange([...rows, { kind: "jsonpath", expression: "", expected: "" }])} style={btn(c, true)}>
        + Aserción
      </button>
    </div>
  );
}

export function ExtractorEditor(props: {
  c: Theme;
  rows: ExtractorRow[];
  onChange: (rows: ExtractorRow[]) => void;
}) {
  const { c, rows, onChange } = props;
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>
        Extractores (correlación para suites): guardan variables tras la respuesta
      </div>
      {rows.map((row, idx) => (
        <div key={idx} style={{ display: "flex", gap: 6, marginBottom: 6, flexWrap: "wrap", alignItems: "center" }}>
          <select
            value={row.kind}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], kind: e.target.value };
              onChange(next);
            }}
            style={inputStyle(c, { width: 100 })}
          >
            {["jsonpath", "regex", "header"].map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
          <input
            value={row.expression}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], expression: e.target.value };
              onChange(next);
            }}
            placeholder="$.token o regex"
            style={inputStyle(c, { flex: "1 1 160px" })}
          />
          <input
            value={row.target_var}
            onChange={(e) => {
              const next = [...rows];
              next[idx] = { ...next[idx], target_var: e.target.value };
              onChange(next);
            }}
            placeholder="variable"
            style={inputStyle(c, { width: 120 })}
          />
          <button type="button" onClick={() => onChange(rows.filter((_, i) => i !== idx))} style={btn(c, true)}>
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...rows, { kind: "jsonpath", expression: "$.", target_var: "var" }])}
        style={btn(c, true)}
      >
        + Extractor
      </button>
    </div>
  );
}

export function SuiteRunnerPanel(props: {
  c: Theme;
  project: string;
  environment: string;
  scenarioIds: string[];
  scenarios: { id: string; name: string }[];
  envVarNames?: string[];
  canRun: boolean;
  busy: boolean;
  onError: (msg: string) => void;
  onHint: (msg: string) => void;
}) {
  const { c, project, environment, scenarioIds, scenarios, envVarNames = [], canRun, busy, onError, onHint } = props;
  const [continueOnFail, setContinueOnFail] = useState(false);
  const [dataFile, setDataFile] = useState("");
  const [dataFiles, setDataFiles] = useState<string[]>([]);
  const [mode, setMode] = useState<"simple" | "flow">("simple");
  const [flowNodes, setFlowNodes] = useState<FlowNode[]>([]);
  const [flowName, setFlowName] = useState("Mi flujo");
  const [savedFlows, setSavedFlows] = useState<{ id: string; name: string }[]>([]);
  const [loadedFlowId, setLoadedFlowId] = useState<string | null>(null);
  const [driverCaps, setDriverCaps] = useState<DriverCapabilities | null>(null);
  const [preflightBusy, setPreflightBusy] = useState(false);
  const [suiteResult, setSuiteResult] = useState<Awaited<ReturnType<typeof runApiSuite>> | null>(null);

  useEffect(() => {
    if (!project) return;
    void getApiDataFiles(project)
      .then((r) => setDataFiles(r.files.map((f) => f.name)))
      .catch(() => setDataFiles([]));
  }, [project]);

  useEffect(() => {
    if (!project || mode !== "flow") return;
    void listApiFlows(project)
      .then((r) => setSavedFlows(r.flows.map((f) => ({ id: f.id, name: f.name }))))
      .catch(() => setSavedFlows([]));
    void getApiDriverCapabilities()
      .then(setDriverCaps)
      .catch(() => setDriverCaps(null));
  }, [project, mode]);

  const refreshFlows = () => {
    if (!project) return;
    void listApiFlows(project)
      .then((r) => setSavedFlows(r.flows.map((f) => ({ id: f.id, name: f.name }))))
      .catch(() => setSavedFlows([]));
  };

  const handleSaveFlow = () => {
    const name = flowName.trim();
    if (!name) {
      onError("Indica un nombre para el flujo.");
      return;
    }
    if (!flowNodes.length) {
      onError("Añade al menos un paso antes de guardar.");
      return;
    }
    const existing = savedFlows.find((f) => f.id === loadedFlowId || f.name.toLowerCase() === name.toLowerCase());
    if (existing && !window.confirm(`El flujo «${existing.name}» ya existe. ¿Sobrescribir?`)) {
      return;
    }
    const flowId = existing?.id ?? loadedFlowId ?? undefined;
    void saveApiFlow({
      project,
      flow_id: flowId,
      flow: {
        name,
        nodes: serializeFlowNodes(flowNodes),
        continue_on_failure: continueOnFail,
      },
    })
      .then((r) => {
        setLoadedFlowId(r.flow_id);
        refreshFlows();
        onHint(`Flujo guardado: ${name}`);
      })
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
  };

  const handleLoadFlow = (flowId: string) => {
    if (!flowId) return;
    void getApiFlow(project, flowId)
      .then((r) => {
        const flow = r.flow as Record<string, unknown>;
        const nodes = deserializeFlowNodes((flow.nodes as Record<string, unknown>[]) ?? []);
        setFlowNodes(nodes);
        setFlowName(String(flow.name || flowId));
        setLoadedFlowId(flowId);
        if (typeof flow.continue_on_failure === "boolean") {
          setContinueOnFail(flow.continue_on_failure);
        }
        onHint(`Flujo cargado: ${flow.name ?? flowId}`);
      })
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
  };

  const handleNewFlow = () => {
    if (flowNodes.length && !window.confirm("¿Descartar el flujo actual y empezar uno nuevo?")) {
      return;
    }
    setFlowNodes([]);
    setFlowName("Mi flujo");
    setLoadedFlowId(null);
  };

  const handleSqlPreflight = (sql: SqlConfig) => {
    setPreflightBusy(true);
    void sqlPreflight({
      project,
      environment,
      sql: serializeFlowNodes([{ type: "sql", sql }])[0].sql as Record<string, unknown>,
    })
      .then((r) => {
        const res = r.result as Record<string, unknown>;
        onHint(res.ok ? "Preflight SQL OK" : `Preflight SQL: ${String(res.error ?? "fallo")}`);
      })
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)))
      .finally(() => setPreflightBusy(false));
  };

  const handleRun = () => {
    if (mode === "flow") {
      if (!flowNodes.length) {
        onError("Añade al menos un paso al flujo con controladores.");
        return;
      }
      const payload: Parameters<typeof runApiSuite>[0] = {
        project,
        environment,
        continue_on_failure: continueOnFail,
        data_file: dataFile.trim() || undefined,
      };
      if (loadedFlowId) {
        payload.flow_id = loadedFlowId;
      } else {
        payload.flow = {
          name: flowName.trim() || "Flujo con controladores",
          nodes: serializeFlowNodes(flowNodes),
          continue_on_failure: continueOnFail,
        };
      }
      void runApiSuite(payload)
        .then((r) => {
          setSuiteResult(r);
          onHint(`Flujo: ${r.passed_steps} OK, ${r.failed_steps} fallos (${r.iterations} iteración/es).`);
        })
        .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
      return;
    }
    if (!scenarioIds.length) {
      onError("Selecciona escenarios para la suite.");
      return;
    }
    void runApiSuite({
      project,
      environment,
      scenario_ids: scenarioIds,
      continue_on_failure: continueOnFail,
      data_file: dataFile.trim() || undefined,
    })
      .then((r) => {
        setSuiteResult(r);
        onHint(`Suite: ${r.passed_steps} OK, ${r.failed_steps} fallos (${r.iterations} iteración/es).`);
      })
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
        <button
          type="button"
          onClick={() => setMode("simple")}
          style={btn(c, false, mode === "simple")}
        >
          Lista simple
        </button>
        <button
          type="button"
          onClick={() => setMode("flow")}
          style={btn(c, false, mode === "flow")}
        >
          Flujo con controladores
        </button>
      </div>

      {mode === "flow" ? (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>
            Construye un flujo con peticiones HTTP, consultas SQL, llamadas gRPC, condiciones (If) y bucles
            (Loop/While). Las condiciones se evalúan sobre la respuesta del paso anterior y las variables de sesión.
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
            <input
              value={flowName}
              onChange={(e) => setFlowName(e.target.value)}
              placeholder="Nombre del flujo"
              style={inputStyle(c, { minWidth: 180 })}
            />
            <select
              value={loadedFlowId ?? ""}
              onChange={(e) => {
                const id = e.target.value;
                if (id) handleLoadFlow(id);
              }}
              style={inputStyle(c, { minWidth: 160 })}
            >
              <option value="">— cargar flujo guardado —</option>
              {savedFlows.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
            <button type="button" onClick={handleSaveFlow} style={btn(c, true)}>
              Guardar flujo
            </button>
            <button type="button" onClick={handleNewFlow} style={btn(c, true)}>
              Nuevo
            </button>
            {loadedFlowId ? (
              <span style={{ fontSize: 11, color: c.muted }}>ID: {loadedFlowId}</span>
            ) : null}
          </div>
          <NodeListEditor
            c={c}
            scenarios={scenarios}
            nodes={flowNodes}
            depth={0}
            onChange={(nodes) => {
              setFlowNodes(nodes);
              setLoadedFlowId(null);
            }}
            envVarNames={envVarNames}
            driverCaps={driverCaps}
            onSqlPreflight={handleSqlPreflight}
            preflightBusy={preflightBusy}
          />
        </div>
      ) : null}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
        <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
          <input type="checkbox" checked={continueOnFail} onChange={(e) => setContinueOnFail(e.target.checked)} />
          Continuar si falla un paso
        </label>
        <select value={dataFile} onChange={(e) => setDataFile(e.target.value)} style={inputStyle(c, { minWidth: 160 })}>
          <option value="">Sin CSV (1 iteración)</option>
          {dataFiles.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <button type="button" disabled={!canRun || busy} onClick={handleRun} style={btn(c)}>
          {mode === "flow" ? "Ejecutar flujo" : "Ejecutar suite"}
        </button>
      </div>
      {suiteResult ? (
        <div style={{ fontSize: 13, padding: 10, borderRadius: 8, border: `1px solid ${c.border}`, background: c.neutralBg }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>
            {suiteResult.ok ? "Suite OK" : "Suite con fallos"} — {suiteResult.passed_steps}/{suiteResult.passed_steps + suiteResult.failed_steps} pasos
          </div>
          {suiteResult.runs.map((run, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ color: c.muted }}>Iteración {i + 1}</div>
              <ul style={{ margin: "4px 0 0 0", paddingLeft: 18 }}>
                {run.steps.map((step, j) => {
                  const label =
                    step.type === "if"
                      ? `Si → rama "${step.branch ?? "?"}"`
                      : step.type === "loop"
                        ? "Bucle"
                        : step.type === "sql"
                          ? "SQL"
                          : step.type === "grpc"
                            ? "gRPC"
                            : step.name;
                  const isControl = step.type === "if" || step.type === "loop";
                  return (
                    <li key={j} style={{ color: isControl ? c.muted : step.ok ? c.text : "#c0392b" }}>
                      {label}
                      {isControl ? "" : ` — ${step.ok ? "OK" : "FAIL"}`}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                void exportApiSuiteEvidence({
                  project,
                  environment,
                  suite: suiteResult as unknown as Record<string, unknown>,
                  format: "pdf",
                })
                  .then((r) => {
                    window.open(getProjectReportUrl("api", project, r.filename), "_blank");
                    onHint(`Evidencia suite PDF: ${r.filename}`);
                  })
                  .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
              }}
              style={btn(c)}
            >
              Exportar suite (PDF)
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                void exportApiSuiteEvidence({
                  project,
                  environment,
                  suite: suiteResult as unknown as Record<string, unknown>,
                  format: "json",
                })
                  .then((r) => onHint(`Evidencia suite JSON: ${r.filename}`))
                  .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
              }}
              style={btn(c, true)}
            >
              Exportar suite (JSON)
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function DataCsvPanel(props: {
  c: Theme;
  project: string;
  busy: boolean;
  onError: (msg: string) => void;
  onHint: (msg: string) => void;
}) {
  const { c, project, busy, onError, onHint } = props;
  const [filename, setFilename] = useState("datos.csv");
  const [content, setContent] = useState("email,password\nuser1@test.com,pass1\n");
  const [files, setFiles] = useState<string[]>([]);

  const refresh = () => {
    void getApiDataFiles(project)
      .then((r) => setFiles(r.files.map((f) => f.name)))
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
  };

  useEffect(() => {
    refresh();
  }, [project]);

  return (
    <div>
      <div style={{ fontSize: 13, color: c.muted, marginBottom: 8 }}>
        CSV en <code>resources/data/</code> para suites data-driven.
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        <input value={filename} onChange={(e) => setFilename(e.target.value)} style={inputStyle(c, { width: 160 })} />
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            void saveApiDataFile({ project, filename, content })
              .then(() => {
                refresh();
                onHint(`CSV guardado: ${filename}`);
              })
              .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
          }}
          style={btn(c)}
        >
          Guardar CSV
        </button>
      </div>
      <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4} style={monoArea(c)} />
      {files.length ? (
        <div style={{ fontSize: 12, color: c.muted, marginTop: 8 }}>Archivos: {files.join(", ")}</div>
      ) : null}
    </div>
  );
}

export function LoadMetricsPanel(props: { c: Theme; runId: string | null }) {
  const { c, runId } = props;
  const [metrics, setMetrics] = useState<Awaited<ReturnType<typeof getLoadTestMetrics>> | null>(null);
  const [runState, setRunState] = useState("running");

  useEffect(() => {
    if (!runId) {
      setMetrics(null);
      return;
    }
    let cancelled = false;
    const poll = () => {
      void getLoadTestMetrics(runId)
        .then((m) => {
          if (cancelled) return;
          setMetrics(m);
          setRunState(m.state);
          if (m.state === "running") window.setTimeout(poll, 1500);
        })
        .catch(() => {
          if (!cancelled) window.setTimeout(poll, 2000);
        });
      void getTestRun(runId).then((r) => {
        if (!cancelled) setRunState(r.state);
      });
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (!runId || !metrics) return null;
  const live = metrics.metrics.live;
  const bars = [
    { label: "RPS", value: live.current_rps, max: Math.max(live.current_rps, 1) },
    { label: "p50 ms", value: live.p50_ms, max: Math.max(live.p95_ms, live.p50_ms, 1) },
    { label: "p95 ms", value: live.p95_ms, max: Math.max(live.p95_ms, live.p99_ms, 1) },
    { label: "p99 ms", value: live.p99_ms, max: Math.max(live.p99_ms, 1) },
  ];

  return (
    <div
      style={{
        marginTop: 12,
        padding: 12,
        borderRadius: 10,
        border: `1px solid ${c.border}`,
        background: c.neutralBg,
        fontSize: 13,
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: 8 }}>
        Métricas en vivo ({runState}) — req: {live.total_requests}, errores: {live.total_failures} ({live.error_rate_pct}%)
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 10 }}>
        {bars.map((b) => (
          <div key={b.label}>
            <div style={{ fontSize: 11, color: c.muted }}>{b.label}</div>
            <div style={{ fontWeight: 700 }}>{Math.round(b.value * 10) / 10}</div>
            <div style={{ height: 6, background: c.border, borderRadius: 4, marginTop: 4 }}>
              <div
                style={{
                  height: "100%",
                  width: `${Math.min(100, (b.value / b.max) * 100)}%`,
                  background: c.primary,
                  borderRadius: 4,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LoadHistoryComparePanel(props: {
  c: Theme;
  project: string;
  refreshToken?: number;
  onError: (msg: string) => void;
}) {
  const { c, project, refreshToken, onError } = props;
  const [runs, setRuns] = useState<Array<{ id: string; label: string }>>([]);
  const [runA, setRunA] = useState("");
  const [runB, setRunB] = useState("");
  const [compare, setCompare] = useState<Awaited<ReturnType<typeof compareApiLoadRuns>> | null>(null);

  useEffect(() => {
    if (!project) return;
    void getApiLoadHistory(project)
      .then((r) => {
        const items = (r.runs || []).map((item) => {
          const id = String(item.id || "");
          const saved = String(item.saved_at || "").slice(0, 19);
          const users = String(item.users ?? "?");
          return { id, label: `${saved} — ${users} usuarios` };
        });
        setRuns(items);
        if (items.length >= 2) {
          setRunA((prev) => prev || items[1].id);
          setRunB((prev) => prev || items[0].id);
        }
      })
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
  }, [project, refreshToken, onError]);

  const handleCompare = () => {
    if (!runA || !runB) {
      onError("Selecciona dos ejecuciones del historial.");
      return;
    }
    void compareApiLoadRuns({ project, run_a: runA, run_b: runB })
      .then(setCompare)
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)));
  };

  if (!runs.length) return null;

  return (
    <div style={{ marginTop: 12, padding: 12, borderRadius: 10, border: `1px solid ${c.border}`, background: c.neutralBg, fontSize: 13 }}>
      <div style={{ fontWeight: 700, marginBottom: 8 }}>Comparativa de cargas (historial local)</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
        <select value={runA} onChange={(e) => setRunA(e.target.value)} style={inputStyle(c, { minWidth: 180 })}>
          <option value="">Ejecución A</option>
          {runs.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </select>
        <select value={runB} onChange={(e) => setRunB(e.target.value)} style={inputStyle(c, { minWidth: 180 })}>
          <option value="">Ejecución B</option>
          {runs.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </select>
        <button type="button" onClick={handleCompare} style={btn(c)}>
          Comparar
        </button>
      </div>
      {compare ? (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 4 }}>Métrica</th>
              <th style={{ textAlign: "right", padding: 4 }}>A</th>
              <th style={{ textAlign: "right", padding: 4 }}>B</th>
              <th style={{ textAlign: "right", padding: 4 }}>Δ</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(compare.delta).map(([key, row]) => (
              <tr key={key}>
                <td style={{ padding: 4 }}>{key}</td>
                <td style={{ padding: 4, textAlign: "right" }}>{row.a}</td>
                <td style={{ padding: 4, textAlign: "right" }}>{row.b}</td>
                <td style={{ padding: 4, textAlign: "right", color: row.diff > 0 ? "#c0392b" : c.text }}>{row.diff}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}

function inputStyle(c: Theme, extra?: React.CSSProperties): React.CSSProperties {
  return {
    padding: "8px 10px",
    borderRadius: 8,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    ...extra,
  };
}

function monoArea(c: Theme): React.CSSProperties {
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

function btn(c: Theme, ghost?: boolean, primary?: boolean): React.CSSProperties {
  return {
    padding: "8px 12px",
    borderRadius: 8,
    border: primary ? "none" : `1px solid ${c.btnGhostBorder}`,
    background: primary ? c.primary : c.btnGhostBg,
    color: primary ? c.primaryFg : c.text,
    fontWeight: 600,
    cursor: "pointer",
    fontSize: 13,
  };
}
