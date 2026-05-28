import React, { useEffect, useState } from "react";
import {
  getApiDataFiles,
  getLoadTestMetrics,
  getTestRun,
  runApiSuite,
  saveApiDataFile,
} from "../api";

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
  canRun: boolean;
  busy: boolean;
  onError: (msg: string) => void;
  onHint: (msg: string) => void;
}) {
  const { c, project, environment, scenarioIds, canRun, busy, onError, onHint } = props;
  const [continueOnFail, setContinueOnFail] = useState(false);
  const [dataFile, setDataFile] = useState("");
  const [dataFiles, setDataFiles] = useState<string[]>([]);
  const [suiteResult, setSuiteResult] = useState<Awaited<ReturnType<typeof runApiSuite>> | null>(null);

  useEffect(() => {
    if (!project) return;
    void getApiDataFiles(project)
      .then((r) => setDataFiles(r.files.map((f) => f.name)))
      .catch(() => setDataFiles([]));
  }, [project]);

  const handleRun = () => {
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
          Ejecutar suite
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
                {run.steps.map((step, j) => (
                  <li key={j} style={{ color: step.ok ? c.text : "#c0392b" }}>
                    {step.name} — {step.ok ? "OK" : "FAIL"}
                  </li>
                ))}
              </ul>
            </div>
          ))}
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
