import React, { useState } from "react";
import { getApiScriptsGuide } from "../../api";
import type { AssertionRow, ExtractorRow } from "../ApiAdvancedPanels";
import { AssertionEditor, ExtractorEditor } from "../ApiAdvancedPanels";
import { SegmentedTabs } from "../../components/ui";
import { ApiScriptsGuideModal } from "./ApiScriptsGuideModal";
import { ApiScriptEditor } from "./ApiScriptEditor";
import { JsonResponseView, isLikelyJsonBody } from "./JsonResponseView";
import { ApiSection, EnvVarEditor, HeaderEditor, apiBtn, apiInputStyle, apiMonoArea, type HeaderRow } from "./apiUi";

type ExecResult = {
  ok: boolean;
  status_code: number;
  elapsed_ms: number;
  body?: string;
  headers?: Record<string, string>;
  assertions?: { passed: boolean; message: string }[];
  script_logs?: string[];
  variables?: Record<string, string>;
};

type PostmanPane = "env" | "request";
type RequestSubTab = "general" | "headers" | "validation" | "scripts";

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
  scenarioName: string;
  onScenarioNameChange: (value: string) => void;
  activeScenarioId: string | null;
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
  preRequestScript: string;
  onPreRequestScriptChange: (value: string) => void;
  postRequestScript: string;
  onPostRequestScriptChange: (value: string) => void;
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
    scenarioName,
    onScenarioNameChange,
    activeScenarioId,
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
    preRequestScript,
    onPreRequestScriptChange,
    postRequestScript,
    onPostRequestScriptChange,
    execResult,
    onExportEvidence,
  } = props;
  const [requestSubTab, setRequestSubTab] = useState<RequestSubTab>("general");
  const [guideOpen, setGuideOpen] = useState(false);
  const [guideTitle, setGuideTitle] = useState("Guía de scripts API");
  const [guideContent, setGuideContent] = useState("");
  const [guideLoading, setGuideLoading] = useState(false);
  const [guideError, setGuideError] = useState<string | null>(null);

  const openScriptsGuide = () => {
    setGuideOpen(true);
    if (guideContent) return;
    setGuideLoading(true);
    setGuideError(null);
    void getApiScriptsGuide()
      .then((r) => {
        setGuideTitle(r.title || "Guía de scripts API");
        setGuideContent(r.content);
      })
      .catch((e: unknown) => setGuideError(String((e as Error)?.message ?? e)))
      .finally(() => setGuideLoading(false));
  };

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
            Usa <code style={{ fontSize: 12 }}>{"{{variable}}"}</code> en URL, headers y body. Guarda el entorno para persistir valores.
          </div>
          <EnvVarEditor
            c={c}
            envVarsText={envVarsText}
            onEnvVarsTextChange={onEnvVarsTextChange}
            previewUrl={url}
          />
          <HeaderEditor
            c={c}
            rows={globalHeaders}
            onChange={onGlobalHeadersChange}
            label="Headers globales"
            collapsible
            collapseThreshold={3}
          />
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
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 10 }}>
            <input
              value={scenarioName}
              onChange={(e) => onScenarioNameChange(e.target.value)}
              placeholder="Nombre del escenario (visible en la lista)"
              style={apiInputStyle(c, { width: "100%" })}
            />
            {activeScenarioId ? (
              <div style={{ fontSize: 11, color: c.muted }}>
                Escenario activo: <code style={{ fontSize: 10 }}>{activeScenarioId}</code>
              </div>
            ) : (
              <div style={{ fontSize: 11, color: c.muted }}>Petición manual (se creará un escenario nuevo al guardar).</div>
            )}
          </div>

          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "flex-start",
              justifyContent: "space-between",
              flexWrap: "wrap",
              fontSize: 12,
              color: c.muted,
              marginBottom: 10,
              lineHeight: 1.45,
            }}
          >
            <div style={{ flex: "1 1 280px" }}>
              Scripts tipo Postman (subset JS): <code style={{ fontSize: 11 }}>pm.environment.set/get</code>,{" "}
              <code style={{ fontSize: 11 }}>pm.variables.set/get</code>,{" "}
              <code style={{ fontSize: 11 }}>pm.request.headers.add</code>,{" "}
              <code style={{ fontSize: 11 }}>pm.response.json()</code>,{" "}
              <code style={{ fontSize: 11 }}>pm.test</code>.
            </div>
            <button type="button" onClick={openScriptsGuide} style={apiBtn(c, c.primary, c.primaryFg)}>
              Ver guía de scripts
            </button>
          </div>

          <SegmentedTabs
            c={c}
            value={requestSubTab}
            onChange={setRequestSubTab}
            options={[
              { id: "general", label: "General", testId: "elia-api-request-general" },
              { id: "headers", label: `Headers (${reqHeaders.filter((r) => r.key.trim()).length})`, testId: "elia-api-request-headers" },
              { id: "validation", label: "Validación", testId: "elia-api-request-validation" },
              { id: "scripts", label: "Scripts", testId: "elia-api-request-scripts" },
            ]}
            style={{ marginBottom: 12 }}
          />

          {requestSubTab === "general" ? (
            <>
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
              <textarea
                value={body}
                onChange={(e) => onBodyChange(e.target.value)}
                placeholder="Body JSON (opcional)"
                rows={6}
                style={apiMonoArea(c)}
              />
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                <button type="button" disabled={!canRunJobs || busy} onClick={onSend} style={apiBtn(c, c.primary, c.primaryFg)}>
                  Enviar
                </button>
                <button type="button" disabled={!canRunJobs || busy} onClick={onSaveScenario} style={apiBtn(c)}>
                  Guardar escenario
                </button>
              </div>
            </>
          ) : null}

          {requestSubTab === "headers" ? (
            <HeaderEditor c={c} rows={reqHeaders} onChange={onReqHeadersChange} label="Headers de petición" />
          ) : null}

          {requestSubTab === "validation" ? (
            <>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                <input
                  value={maxDurationMs}
                  onChange={(e) => onMaxDurationMsChange(e.target.value)}
                  placeholder="Max ms (opcional)"
                  style={apiInputStyle(c, { width: 160 })}
                />
              </div>
              <AssertionEditor c={c} rows={assertions} onChange={onAssertionsChange} />
              <ExtractorEditor c={c} rows={extractors} onChange={onExtractorsChange} />
            </>
          ) : null}

          {requestSubTab === "scripts" ? (
            <>
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
                <button type="button" onClick={openScriptsGuide} style={apiBtn(c)}>
                  Abrir guía completa
                </button>
              </div>
              <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>Pre-request (antes de enviar)</div>
              <ApiScriptEditor
                value={preRequestScript}
                onChange={onPreRequestScriptChange}
                minHeight="160px"
                placeholder={'pm.environment.set("token", "abc123");\npm.request.headers.add({key: "Authorization", value: "Bearer " + pm.environment.get("token")});'}
              />
              <div style={{ fontSize: 12, color: c.muted, margin: "12px 0 6px" }}>Post-request / Tests (después de la respuesta)</div>
              <ApiScriptEditor
                value={postRequestScript}
                onChange={onPostRequestScriptChange}
                minHeight="200px"
                placeholder={'const data = pm.response.json();\npm.environment.set("id", data.id);\npm.test("HTTP 200", function () { pm.response.to.have.status(200); });'}
              />
            </>
          ) : null}

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
              {execResult.script_logs?.length ? (
                <details style={{ marginBottom: 8 }}>
                  <summary style={{ cursor: "pointer", color: c.muted }}>Log de scripts</summary>
                  <pre style={{ fontSize: 11, fontFamily: "monospace", whiteSpace: "pre-wrap" }}>
                    {execResult.script_logs.join("\n")}
                  </pre>
                </details>
              ) : null}
              {execResult.body && isLikelyJsonBody(execResult.body) ? (
                <JsonResponseView text={execResult.body} />
              ) : (
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
              )}
            </div>
          ) : null}
        </ApiSection>
      )}
      {guideOpen ? (
        <ApiScriptsGuideModal
          c={c}
          title={guideTitle}
          content={guideContent}
          loading={guideLoading}
          error={guideError}
          onClose={() => setGuideOpen(false)}
        />
      ) : null}
    </div>
  );
}

export type { PostmanPane };
