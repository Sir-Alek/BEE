import React, { useRef } from "react";
import { apiBtn, apiInputStyle } from "./apiUi";

type Props = {
  c: Record<string, string>;
  busy: boolean;
  canRunJobs: boolean;
  scenarios: { id: string; name: string }[];
  captures: { id: string; name: string; path: string }[];
  importKind: "postman" | "openapi";
  onImportKindChange: (kind: "postman" | "openapi") => void;
  onImportFile: (file: File) => void;
  onImportCapture: (captureId: string) => void;
  onLoadScenario: (scenarioId: string) => void;
};

export function ApiPostmanSidebar(props: Props) {
  const {
    c,
    busy,
    canRunJobs,
    scenarios,
    captures,
    importKind,
    onImportKindChange,
    onImportFile,
    onImportCapture,
    onLoadScenario,
  } = props;
  const importRef = useRef<HTMLInputElement>(null);

  return (
    <div
      data-testid="elia-api-postman-sidebar"
      style={{
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        background: c.surface,
        padding: 12,
        minHeight: "min(62vh, 640px)",
        maxHeight: "min(72vh, 720px)",
        overflow: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <div>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Importar colección</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <select
            value={importKind}
            onChange={(e) => onImportKindChange(e.target.value as "postman" | "openapi")}
            style={apiInputStyle(c)}
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
              if (file) onImportFile(file);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            disabled={!canRunJobs || busy}
            onClick={() => importRef.current?.click()}
            style={apiBtn(c)}
          >
            Importar JSON
          </button>
        </div>
      </div>

      <div>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Capturas web</div>
        <div style={{ fontSize: 11, color: c.muted, marginBottom: 8, lineHeight: 1.4 }}>
          JSON en <code style={{ fontSize: 10 }}>behave/api/&lt;proyecto&gt;/scripts/</code>
        </div>
        {captures.length === 0 ? (
          <div style={{ fontSize: 12, color: c.muted }}>Sin capturas en este proyecto.</div>
        ) : (
          <ul style={{ margin: 0, padding: 0, listStyle: "none", fontSize: 12 }}>
            {captures.map((cap) => (
              <li
                key={cap.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  marginBottom: 10,
                  paddingBottom: 10,
                  borderBottom: `1px solid ${c.border}`,
                }}
              >
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={cap.path}>
                  {cap.name}
                </span>
                <button
                  type="button"
                  disabled={!canRunJobs || busy}
                  onClick={() => onImportCapture(cap.id)}
                  style={apiBtn(c, undefined, undefined, true)}
                >
                  Importar a escenarios
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ flex: "1 1 auto", minHeight: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
          Escenarios ({scenarios.length})
        </div>
        {scenarios.length === 0 ? (
          <div style={{ fontSize: 12, color: c.muted }}>Sin escenarios guardados.</div>
        ) : (
          <ul style={{ margin: 0, padding: 0, listStyle: "none", fontSize: 12 }}>
            {scenarios.map((s) => (
              <li key={s.id} style={{ marginBottom: 4 }}>
                <button
                  type="button"
                  disabled={busy}
                  title={s.name}
                  onClick={() => onLoadScenario(s.id)}
                  style={{
                    ...apiBtn(c, undefined, undefined, true),
                    width: "100%",
                    textAlign: "left",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {s.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
