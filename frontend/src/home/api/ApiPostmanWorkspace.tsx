import React from "react";
import type { AssertionRow, ExtractorRow } from "../ApiAdvancedPanels";
import { AssertionEditor, ExtractorEditor } from "../ApiAdvancedPanels";
import { SegmentedTabs } from "../../components/ui";
import { ApiSection, HeaderEditor, apiBtn, apiInputStyle, apiMonoArea, type HeaderRow } from "./apiUi";

type ExecResult = {
  ok: boolean;
  status_code: number;
  elapsed_ms: number;
  body?: string;
  headers?: Record<string, string>;
  assertions?: { passed: boolean; message: string }[];
};

type PostmanPane = "env" | "request";

type Props = {
  c: Record<string, string>;
  busy: boolean;
  canRunJobs: boolean;
  pane: PostmanPane;
  onPaneChange: (pane: PostmanPane) => void;
  envVarsText: string;
  onEnvVarsTextChange: (value: string) => void;
  globalHeaders: HeaderRow[];
  onGlobalHeadersChange: (rows: HeaderRow[]) => void;
  webOriginAvailable: boolean;
  onSaveEnvironment: () => void;
  onSaveGlobalConfig: () => void;
  onSyncFromWeb: () => void;
  method: string;
  methods: string[];
  onMethodChange: (method: string) => void;
  url: string;
  onUrlChange: (url: string) => void;
  expectedStatus: string;
  onExpectedStatusChange: (value: string) => void;
  reqHeaders: HeaderRow[];
  onReqHeadersChange: (rows: HeaderRow[]) => void;
  maxDurationMs: string;
  onMaxDurationMsChange: (value: string) => void;
  assertions: AssertionRow[];
  onAssertionsChange: (rows: AssertionRow[]) => void;
  extractors: ExtractorRow[];
  onExtractorsChange: (rows: ExtractorRow[]) => void;
  body: string;
  onBodyChange: (value: string) => void;
  onSend: () => void;
  onSaveScenario: () => void;
  execResult: ExecResult | null;
  onExportEvidence: (format: "pdf" | "json") => void;
};

export function ApiPostmanWorkspace(props: Props) {
  const {
    c,
    busy,
    canRunJobs,
    pane,
    onPaneChange,
    envVarsText,
    onEnvVarsTextChange,
    globalHeaders,
    onGlobalHeadersChange,
    webOriginAvailable,
    onSaveEnvironment,
    onSaveGlobalConfig,
    onSyncFromWeb,
    method,
    methods,
    onMethodChange,
    url,
    onUrlChange,
    expectedStatus,
    onExpectedStatusChange,
    reqHeaders,
    onReqHeadersChange,
    maxDurationMs,
    onMaxDurationMsChange,
    assertions,
    onAssertionsChange,
    extractors,
    onExtractorsChange,
    body,
    onBodyChange,
    onSend,
    onSaveScenario,
    execResult,
    onExportEvidence,
  } = props;

  return (
    <div data-testid="elia-api-postman-workspace">
      <SegmentedTabs
        c={c}
        value={pane}
        onChange={onPaneChange}
        options={[
          { id: "env", label: "Entorno", testId: "elia-api-pane-env" },
          { id: "request", label: "Petición", testId: "elia-api-pane-request" },
        ]}
        style={{ marginBottom: 14 }}
      />

      {pane === "env" ? (
        <ApiSection c={c} title="Entorno y headers globales">
          <div style={{ fontSize: 13, color: c.muted, marginBottom: 8 }}>
            Usa <code style={{ fontSize: 12 }}>{"{{variable}}"}</code> en URL, headers y body. Se resuelven desde el entorno activo.
          </div>
          <textarea
            value={envVarsText}
            onChange={(e) => onEnvVarsTextChange(e.target.value)}
            rows={6}
            style={apiMonoArea(c)}
            placeholder='{"base_url": "https://api.ejemplo.com"}'
          />
          <HeaderEditor c={c} rows={globalHeaders} onChange={onGlobalHeadersChange} label="Headers globales" />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
            <button type="button" disabled={busy} onClick={onSaveEnvironment} style={apiBtn(c)}>
              Guardar entorno
            </button>
            <button type="button" disabled={busy} onClick={onSaveGlobalConfig} style={apiBtn(c)}>
              Guardar config proyecto
            </button>
            {webOriginAvailable ? (
              <button type="button" disabled={busy} onClick={onSyncFromWeb} style={apiBtn(c, undefined, undefined, true)}>
                Sincronizar base_url desde grabación web
              </button>
            ) : null}
          </div>
        </ApiSection>
      ) : (
        <ApiSection c={c} title="Petición HTTP">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            <select value={method} onChange={(e) => onMethodChange(e.target.value)} style={apiInputStyle(c, { width: 100 })}>
              {methods.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
            <input
              value={url}
              onChange={(e) => onUrlChange(e.target.value)}
              placeholder="{{base_url}}/recurso"
              style={apiInputStyle(c, { flex: "1 1 280px" })}
            />
            <input
              value={expectedStatus}
              onChange={(e) => onExpectedStatusChange(e.target.value)}
              placeholder="200"
              style={apiInputStyle(c, { width: 72 })}
            />
          </div>
          <HeaderEditor c={c} rows={reqHeaders} onChange={onReqHeadersChange} label="Headers de petición" />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
            <input
              value={maxDurationMs}
              onChange={(e) => onMaxDurationMsChange(e.target.value)}
              placeholder="Max ms (opcional)"
              style={apiInputStyle(c, { width: 130 })}
            />
          </div>
          <AssertionEditor c={c} rows={assertions} onChange={onAssertionsChange} />
          <ExtractorEditor c={c} rows={extractors} onChange={onExtractorsChange} />
          <textarea
            value={body}
            onChange={(e) => onBodyChange(e.target.value)}
            placeholder="Body JSON (opcional)"
            rows={5}
            style={{ ...apiMonoArea(c), marginTop: 8 }}
          />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
            <button type="button" disabled={!canRunJobs || busy} onClick={onSend} style={apiBtn(c, c.primary, c.primaryFg)}>
              Enviar
            </button>
            <button type="button" disabled={!canRunJobs || busy} onClick={onSaveScenario} style={apiBtn(c)}>
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
                <button type="button" disabled={busy} onClick={() => onExportEvidence("pdf")} style={apiBtn(c)}>
                  Exportar evidencia (PDF)
                </button>
                <button type="button" disabled={busy} onClick={() => onExportEvidence("json")} style={apiBtn(c)}>
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
        </ApiSection>
      )}
    </div>
  );
}

export type { PostmanPane };
