import React from "react";
import { apiBtn, apiInputStyle, apiMonoArea } from "./apiUi";

type Theme = Record<string, string>;

export type FlowCondition = {
  kind: string;
  expression?: string;
  expected?: string;
  negate?: boolean;
};

export type SqlExtractorRow = { column: string; target_var: string; row: string };
export type GrpcExtractorRow = { jsonpath: string; target_var: string };

export type SqlConfig = {
  driver: string;
  dsn?: string;
  host?: string;
  port?: string;
  database?: string;
  user_env?: string;
  password_env?: string;
  query?: string;
  params_json?: string;
  extractors?: SqlExtractorRow[];
  min_rows?: string;
  max_rows?: string;
};

export type GrpcConfig = {
  target?: string;
  service?: string;
  method?: string;
  message_json?: string;
  metadata_json?: string;
  tls?: boolean;
  timeout_sec?: number;
  extractors?: GrpcExtractorRow[];
};

export type DriverCapabilities = {
  sql: Record<string, boolean>;
  grpc: { available: boolean; missing: string[] };
  install_hint?: string;
};

export type FlowNode = {
  type: "request" | "if" | "loop" | "sql" | "grpc";
  scenario_id?: string;
  name?: string;
  condition?: FlowCondition;
  then?: FlowNode[];
  else?: FlowNode[];
  mode?: "count" | "while";
  count?: string;
  max_iterations?: number;
  body?: FlowNode[];
  sql?: SqlConfig;
  grpc?: GrpcConfig;
};

const CONDITION_KINDS: { id: string; label: string; needsExpr: boolean; needsExpected: boolean }[] = [
  { id: "always", label: "Siempre", needsExpr: false, needsExpected: false },
  { id: "status", label: "Status ==", needsExpr: false, needsExpected: true },
  { id: "status_lt", label: "Status <", needsExpr: false, needsExpected: true },
  { id: "status_gte", label: "Status >=", needsExpr: false, needsExpected: true },
  { id: "jsonpath_exists", label: "JSONPath existe", needsExpr: true, needsExpected: false },
  { id: "jsonpath_equals", label: "JSONPath ==", needsExpr: true, needsExpected: true },
  { id: "body_contains", label: "Body contiene", needsExpr: false, needsExpected: true },
  { id: "regex", label: "Regex en body", needsExpr: true, needsExpected: false },
  { id: "var_exists", label: "Variable existe", needsExpr: true, needsExpected: false },
  { id: "var_equals", label: "Variable ==", needsExpr: true, needsExpected: true },
  { id: "var_gt", label: "Variable >", needsExpr: true, needsExpected: true },
  { id: "var_lt", label: "Variable <", needsExpr: true, needsExpected: true },
];

const SQL_DRIVERS = [
  { id: "sqlite", label: "SQLite (nativo)" },
  { id: "postgres", label: "PostgreSQL" },
  { id: "mysql", label: "MySQL" },
  { id: "sqlserver", label: "SQL Server" },
];

function parseJsonObject(text: string | undefined): Record<string, unknown> | undefined {
  const t = (text ?? "").trim();
  if (!t) return undefined;
  try {
    const v = JSON.parse(t);
    return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : undefined;
  } catch {
    return undefined;
  }
}

/** Convierte nodos del editor al formato que espera el backend (suite_runner). */
export function serializeFlowNodes(nodes: FlowNode[]): Record<string, unknown>[] {
  return nodes.map(serializeNode);
}

function serializeNode(node: FlowNode): Record<string, unknown> {
  const base: Record<string, unknown> = { type: node.type };
  if (node.type === "request") {
    return { ...base, scenario_id: node.scenario_id };
  }
  if (node.type === "if") {
    return {
      ...base,
      condition: node.condition,
      then: serializeFlowNodes(node.then ?? []),
      else: serializeFlowNodes(node.else ?? []),
    };
  }
  if (node.type === "loop") {
    return {
      ...base,
      mode: node.mode ?? "count",
      count: node.count,
      max_iterations: node.max_iterations ?? 100,
      condition: node.condition,
      body: serializeFlowNodes(node.body ?? []),
    };
  }
  if (node.type === "sql") {
    const s = node.sql ?? { driver: "sqlite" };
    const sql: Record<string, unknown> = {
      driver: s.driver || "sqlite",
      query: s.query || "",
    };
    if (s.dsn?.trim()) sql.dsn = s.dsn.trim();
    if (s.host?.trim()) sql.host = s.host.trim();
    if (s.port?.trim()) sql.port = parseInt(s.port, 10);
    if (s.database?.trim()) sql.database = s.database.trim();
    if (s.user_env?.trim()) sql.user_env = s.user_env.trim();
    if (s.password_env?.trim()) sql.password_env = s.password_env.trim();
    const params = parseJsonObject(s.params_json);
    if (params) sql.params = params;
    const extractors = (s.extractors ?? []).filter((e) => e.column?.trim() && e.target_var?.trim());
    if (extractors.length) {
      sql.extract = extractors.map((e) => ({
        column: e.column.trim(),
        target_var: e.target_var.trim(),
        row: parseInt(e.row || "0", 10) || 0,
      }));
    }
    const assert: Record<string, unknown> = {};
    if (s.min_rows?.trim()) assert.min_rows = parseInt(s.min_rows, 10);
    if (s.max_rows?.trim()) assert.max_rows = parseInt(s.max_rows, 10);
    if (Object.keys(assert).length) sql.assert = assert;
    return { ...base, sql };
  }
  if (node.type === "grpc") {
    const g = node.grpc ?? {};
    const grpc: Record<string, unknown> = {
      target: g.target?.trim() || "",
      service: g.service?.trim() || "",
      method: g.method?.trim() || "",
      tls: !!g.tls,
      timeout_sec: g.timeout_sec ?? 15,
    };
    const message = parseJsonObject(g.message_json);
    if (message) grpc.message = message;
    const metadata = parseJsonObject(g.metadata_json);
    if (metadata) {
      grpc.metadata = Object.fromEntries(Object.entries(metadata).map(([k, v]) => [k, String(v)]));
    }
    const grpcExtractors = (g.extractors ?? []).filter((e) => e.jsonpath?.trim() && e.target_var?.trim());
    if (grpcExtractors.length) {
      grpc.extract = grpcExtractors.map((e) => ({
        jsonpath: e.jsonpath.trim(),
        target_var: e.target_var.trim(),
      }));
    }
    return { ...base, grpc };
  }
  return base;
}

/** Convierte nodos del backend/API al estado del editor visual. */
export function deserializeFlowNodes(nodes: Record<string, unknown>[]): FlowNode[] {
  return (nodes || []).map(deserializeNode);
}

function deserializeNode(raw: Record<string, unknown>): FlowNode {
  const ntype = String(raw.type || "request").toLowerCase() as FlowNode["type"];
  if (ntype === "if") {
    return {
      type: "if",
      condition: (raw.condition as FlowCondition) ?? { kind: "always" },
      then: deserializeFlowNodes((raw.then as Record<string, unknown>[]) ?? []),
      else: deserializeFlowNodes((raw.else as Record<string, unknown>[]) ?? []),
    };
  }
  if (ntype === "loop") {
    return {
      type: "loop",
      mode: (raw.mode as "count" | "while") ?? "count",
      count: raw.count != null ? String(raw.count) : "1",
      max_iterations: Number(raw.max_iterations ?? 100),
      condition: raw.condition as FlowCondition | undefined,
      body: deserializeFlowNodes((raw.body as Record<string, unknown>[]) ?? []),
    };
  }
  if (ntype === "sql") {
    const sql = (raw.sql as Record<string, unknown>) ?? {};
    const extractRaw = (sql.extract as Record<string, unknown>[]) ?? [];
    const assert = (sql.assert as Record<string, unknown>) ?? {};
    return {
      type: "sql",
      sql: {
        driver: String(sql.driver || "sqlite"),
        dsn: sql.dsn != null ? String(sql.dsn) : undefined,
        host: sql.host != null ? String(sql.host) : undefined,
        port: sql.port != null ? String(sql.port) : undefined,
        database: sql.database != null ? String(sql.database) : undefined,
        user_env: sql.user_env != null ? String(sql.user_env) : undefined,
        password_env: sql.password_env != null ? String(sql.password_env) : undefined,
        query: sql.query != null ? String(sql.query) : "",
        params_json: sql.params ? JSON.stringify(sql.params, null, 2) : "",
        extractors: extractRaw.map((e) => ({
          column: String(e.column ?? ""),
          target_var: String(e.target_var ?? ""),
          row: String(e.row ?? "0"),
        })),
        min_rows: assert.min_rows != null ? String(assert.min_rows) : "",
        max_rows: assert.max_rows != null ? String(assert.max_rows) : "",
      },
    };
  }
  if (ntype === "grpc") {
    const grpc = (raw.grpc as Record<string, unknown>) ?? {};
    const extractRaw = (grpc.extract as Record<string, unknown>[]) ?? [];
    return {
      type: "grpc",
      grpc: {
        target: grpc.target != null ? String(grpc.target) : "",
        service: grpc.service != null ? String(grpc.service) : "",
        method: grpc.method != null ? String(grpc.method) : "",
        message_json: grpc.message ? JSON.stringify(grpc.message, null, 2) : "{}",
        metadata_json: grpc.metadata ? JSON.stringify(grpc.metadata, null, 2) : "",
        tls: Boolean(grpc.tls),
        timeout_sec: Number(grpc.timeout_sec ?? 15),
        extractors: extractRaw.map((e) => ({
          jsonpath: String(e.jsonpath ?? ""),
          target_var: String(e.target_var ?? ""),
        })),
      },
    };
  }
  return {
    type: "request",
    scenario_id: raw.scenario_id != null ? String(raw.scenario_id) : "",
  };
}

export function analyzeFlowNodeCounts(nodes: FlowNode[]): Record<string, number> {
  const counts: Record<string, number> = {};
  const walk = (list: FlowNode[]) => {
    for (const n of list) {
      counts[n.type] = (counts[n.type] ?? 0) + 1;
      if (n.then) walk(n.then);
      if (n.else) walk(n.else);
      if (n.body) walk(n.body);
    }
  };
  walk(nodes);
  return counts;
}

function defaultNode(type: FlowNode["type"], firstScenario: string): FlowNode {
  if (type === "if") {
    return { type: "if", condition: { kind: "status", expected: "200" }, then: [], else: [] };
  }
  if (type === "loop") {
    return { type: "loop", mode: "count", count: "3", max_iterations: 100, body: [] };
  }
  if (type === "sql") {
    return {
      type: "sql",
      sql: {
        driver: "sqlite",
        dsn: ":memory:",
        query: "SELECT 1 AS ok",
        params_json: "",
        extractors: [],
      },
    };
  }
  if (type === "grpc") {
    return {
      type: "grpc",
      grpc: {
        target: "localhost:50051",
        service: "paquete.Servicio",
        method: "MiMetodo",
        message_json: "{}",
        timeout_sec: 15,
        extractors: [],
      },
    };
  }
  return { type: "request", scenario_id: firstScenario };
}

function ConditionEditor(props: { c: Theme; condition: FlowCondition; onChange: (cond: FlowCondition) => void }) {
  const { c, condition, onChange } = props;
  const meta = CONDITION_KINDS.find((k) => k.id === condition.kind) ?? CONDITION_KINDS[0];
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
      <select
        value={condition.kind}
        onChange={(e) => onChange({ ...condition, kind: e.target.value })}
        style={apiInputStyle(c, { minWidth: 150 })}
      >
        {CONDITION_KINDS.map((k) => (
          <option key={k.id} value={k.id}>
            {k.label}
          </option>
        ))}
      </select>
      {meta.needsExpr ? (
        <input
          value={condition.expression ?? ""}
          onChange={(e) => onChange({ ...condition, expression: e.target.value })}
          placeholder={condition.kind.startsWith("var") ? "nombre_variable" : "$.ruta / patrón"}
          style={apiInputStyle(c, { flex: "1 1 130px" })}
        />
      ) : null}
      {meta.needsExpected ? (
        <input
          value={condition.expected ?? ""}
          onChange={(e) => onChange({ ...condition, expected: e.target.value })}
          placeholder="valor esperado"
          style={apiInputStyle(c, { flex: "1 1 110px" })}
        />
      ) : null}
      <label style={{ fontSize: 12, color: c.muted, display: "flex", alignItems: "center", gap: 4 }}>
        <input
          type="checkbox"
          checked={!!condition.negate}
          onChange={(e) => onChange({ ...condition, negate: e.target.checked })}
        />
        negar
      </label>
    </div>
  );
}

function DriverBadge(props: { c: Theme; ok: boolean; label: string; hint?: string }) {
  const { c, ok, label, hint } = props;
  return (
    <span
      title={hint}
      style={{
        fontSize: 11,
        padding: "2px 8px",
        borderRadius: 6,
        background: ok ? "rgba(46, 125, 50, 0.15)" : "rgba(230, 126, 34, 0.15)",
        color: ok ? "#2e7d32" : "#e67e22",
        fontWeight: 600,
      }}
    >
      {label}
    </span>
  );
}

function SqlNodeEditor(props: {
  c: Theme;
  sql: SqlConfig;
  onChange: (sql: SqlConfig) => void;
  envVarNames?: string[];
  driverCaps?: DriverCapabilities | null;
  onPreflight?: () => void;
  preflightBusy?: boolean;
}) {
  const { c, sql, onChange, envVarNames = [], driverCaps, onPreflight, preflightBusy } = props;
  const isSqlite = (sql.driver || "sqlite") === "sqlite";
  const patch = (p: Partial<SqlConfig>) => onChange({ ...sql, ...p });
  const extractors = sql.extractors ?? [];
  const driverOk = driverCaps?.sql?.[sql.driver || "sqlite"] ?? sql.driver === "sqlite";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: c.primary }}>SQL</span>
        <select
          value={sql.driver || "sqlite"}
          onChange={(e) => patch({ driver: e.target.value })}
          style={apiInputStyle(c, { minWidth: 160 })}
        >
          {SQL_DRIVERS.map((d) => (
            <option key={d.id} value={d.id}>
              {d.label}
            </option>
          ))}
        </select>
        <DriverBadge
          c={c}
          ok={!!driverOk}
          label={driverOk ? "Driver OK" : "Requiere pip"}
          hint={driverOk ? undefined : driverCaps?.install_hint}
        />
      </div>
      {isSqlite ? (
        <input
          value={sql.dsn ?? ""}
          onChange={(e) => patch({ dsn: e.target.value })}
          placeholder="Ruta .db o :memory:"
          style={apiInputStyle(c, { width: "100%" })}
        />
      ) : (
        <>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <input
              value={sql.host ?? ""}
              onChange={(e) => patch({ host: e.target.value })}
              placeholder="Host"
              style={apiInputStyle(c, { flex: "1 1 140px" })}
            />
            <input
              value={sql.port ?? ""}
              onChange={(e) => patch({ port: e.target.value })}
              placeholder="Puerto"
              style={apiInputStyle(c, { width: 80 })}
            />
            <input
              value={sql.database ?? ""}
              onChange={(e) => patch({ database: e.target.value })}
              placeholder="Base de datos"
              style={apiInputStyle(c, { flex: "1 1 140px" })}
            />
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <select
              value={sql.user_env ?? ""}
              onChange={(e) => patch({ user_env: e.target.value })}
              style={apiInputStyle(c, { flex: "1 1 180px" })}
            >
              <option value="">— clave usuario (entorno API / OS) —</option>
              {envVarNames.map((v) => (
                <option key={`u-${v}`} value={v}>
                  {v}
                </option>
              ))}
            </select>
            <input
              value={sql.user_env ?? ""}
              onChange={(e) => patch({ user_env: e.target.value })}
              placeholder="o escribe nombre de variable"
              style={apiInputStyle(c, { flex: "1 1 160px" })}
            />
            <select
              value={sql.password_env ?? ""}
              onChange={(e) => patch({ password_env: e.target.value })}
              style={apiInputStyle(c, { flex: "1 1 180px" })}
            >
              <option value="">— clave contraseña —</option>
              {envVarNames.map((v) => (
                <option key={`p-${v}`} value={v}>
                  {v}
                </option>
              ))}
            </select>
            <input
              value={sql.password_env ?? ""}
              onChange={(e) => patch({ password_env: e.target.value })}
              placeholder="nombre variable contraseña"
              style={apiInputStyle(c, { flex: "1 1 160px" })}
            />
          </div>
        </>
      )}
      <textarea
        value={sql.query ?? ""}
        onChange={(e) => patch({ query: e.target.value })}
        placeholder="SELECT id FROM users WHERE email = :email"
        rows={3}
        style={apiMonoArea(c)}
      />
      <textarea
        value={sql.params_json ?? ""}
        onChange={(e) => patch({ params_json: e.target.value })}
        placeholder='Parámetros JSON: {"email": "{{email}}"}'
        rows={2}
        style={apiMonoArea(c)}
      />
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 4 }}>Extractores (columna → variable)</div>
      {extractors.map((row, idx) => (
        <div key={idx} style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
          <input
            value={row.column}
            onChange={(e) => {
              const next = [...extractors];
              next[idx] = { ...next[idx], column: e.target.value };
              patch({ extractors: next });
            }}
            placeholder="columna"
            style={apiInputStyle(c, { flex: "1 1 100px" })}
          />
          <input
            value={row.target_var}
            onChange={(e) => {
              const next = [...extractors];
              next[idx] = { ...next[idx], target_var: e.target.value };
              patch({ extractors: next });
            }}
            placeholder="→ variable"
            style={apiInputStyle(c, { flex: "1 1 100px" })}
          />
          <input
            value={row.row}
            onChange={(e) => {
              const next = [...extractors];
              next[idx] = { ...next[idx], row: e.target.value };
              patch({ extractors: next });
            }}
            placeholder="fila"
            style={apiInputStyle(c, { width: 56 })}
          />
          <button
            type="button"
            onClick={() => patch({ extractors: extractors.filter((_, i) => i !== idx) })}
            style={apiBtn(c, undefined, undefined, true)}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => patch({ extractors: [...extractors, { column: "", target_var: "", row: "0" }] })}
        style={apiBtn(c, undefined, undefined, true)}
      >
        + Extractor SQL
      </button>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <input
          value={sql.min_rows ?? ""}
          onChange={(e) => patch({ min_rows: e.target.value })}
          placeholder="mín. filas"
          style={apiInputStyle(c, { width: 90 })}
        />
        <input
          value={sql.max_rows ?? ""}
          onChange={(e) => patch({ max_rows: e.target.value })}
          placeholder="máx. filas"
          style={apiInputStyle(c, { width: 90 })}
        />
        {onPreflight ? (
          <button type="button" disabled={preflightBusy} onClick={onPreflight} style={apiBtn(c, undefined, undefined, true)}>
            Validar conexión
          </button>
        ) : null}
      </div>
      <div style={{ fontSize: 11, color: c.muted }}>
        Credenciales: claves del entorno API activo (dev.json) o variables del sistema. No se guardan valores en el flujo.
      </div>
    </div>
  );
}

function GrpcNodeEditor(props: {
  c: Theme;
  grpc: GrpcConfig;
  onChange: (grpc: GrpcConfig) => void;
  driverCaps?: DriverCapabilities | null;
}) {
  const { c, grpc, onChange, driverCaps } = props;
  const patch = (p: Partial<GrpcConfig>) => onChange({ ...grpc, ...p });
  const extractors = grpc.extractors ?? [];
  const grpcOk = driverCaps?.grpc?.available ?? false;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: c.primary }}>gRPC</span>
        <DriverBadge
          c={c}
          ok={grpcOk}
          label={grpcOk ? "gRPC OK" : "Requiere pip"}
          hint={grpcOk ? undefined : driverCaps?.install_hint}
        />
        <input
          value={grpc.target ?? ""}
          onChange={(e) => patch({ target: e.target.value })}
          placeholder="host:puerto"
          style={apiInputStyle(c, { flex: "1 1 160px" })}
        />
        <input
          type="number"
          min={1}
          value={grpc.timeout_sec ?? 15}
          onChange={(e) => patch({ timeout_sec: Number(e.target.value) || 15 })}
          title="Timeout (s)"
          style={apiInputStyle(c, { width: 72 })}
        />
        <label style={{ fontSize: 12, color: c.muted, display: "flex", alignItems: "center", gap: 4 }}>
          <input type="checkbox" checked={!!grpc.tls} onChange={(e) => patch({ tls: e.target.checked })} />
          TLS
        </label>
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <input
          value={grpc.service ?? ""}
          onChange={(e) => patch({ service: e.target.value })}
          placeholder="paquete.Servicio"
          style={apiInputStyle(c, { flex: "1 1 200px" })}
        />
        <input
          value={grpc.method ?? ""}
          onChange={(e) => patch({ method: e.target.value })}
          placeholder="Metodo"
          style={apiInputStyle(c, { flex: "1 1 140px" })}
        />
      </div>
      <textarea
        value={grpc.message_json ?? ""}
        onChange={(e) => patch({ message_json: e.target.value })}
        placeholder='Mensaje JSON: {"campo": "{{valor}}"}'
        rows={3}
        style={apiMonoArea(c)}
      />
      <textarea
        value={grpc.metadata_json ?? ""}
        onChange={(e) => patch({ metadata_json: e.target.value })}
        placeholder='Metadata JSON: {"authorization": "Bearer {{token}}"}'
        rows={2}
        style={apiMonoArea(c)}
      />
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 4 }}>Extractores (JSONPath → variable)</div>
      {extractors.map((row, idx) => (
        <div key={idx} style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
          <input
            value={row.jsonpath}
            onChange={(e) => {
              const next = [...extractors];
              next[idx] = { ...next[idx], jsonpath: e.target.value };
              patch({ extractors: next });
            }}
            placeholder="$.campo"
            style={apiInputStyle(c, { flex: "1 1 140px" })}
          />
          <input
            value={row.target_var}
            onChange={(e) => {
              const next = [...extractors];
              next[idx] = { ...next[idx], target_var: e.target.value };
              patch({ extractors: next });
            }}
            placeholder="→ variable"
            style={apiInputStyle(c, { flex: "1 1 100px" })}
          />
          <button
            type="button"
            onClick={() => patch({ extractors: extractors.filter((_, i) => i !== idx) })}
            style={apiBtn(c, undefined, undefined, true)}
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => patch({ extractors: [...extractors, { jsonpath: "", target_var: "" }] })}
        style={apiBtn(c, undefined, undefined, true)}
      >
        + Extractor gRPC
      </button>
      <div style={{ fontSize: 11, color: c.muted }}>
        Reflexión del servidor (grpcio, grpcio-reflection, protobuf). Incluido en pruebas de carga Enterprise.
      </div>
    </div>
  );
}

function NodeEditor(props: {
  c: Theme;
  scenarios: { id: string; name: string }[];
  node: FlowNode;
  depth: number;
  onChange: (node: FlowNode) => void;
  envVarNames?: string[];
  driverCaps?: DriverCapabilities | null;
  onSqlPreflight?: (sql: SqlConfig) => void;
  preflightBusy?: boolean;
}) {
  const { c, scenarios, node, depth, onChange, envVarNames, driverCaps, onSqlPreflight, preflightBusy } = props;

  if (node.type === "request") {
    return (
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: c.primary }}>Petición</span>
        <select
          value={node.scenario_id ?? ""}
          onChange={(e) => onChange({ ...node, scenario_id: e.target.value })}
          style={apiInputStyle(c, { flex: "1 1 200px" })}
        >
          <option value="">— escenario —</option>
          {scenarios.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (node.type === "sql") {
    return (
      <SqlNodeEditor
        c={c}
        sql={node.sql ?? { driver: "sqlite", extractors: [] }}
        onChange={(sql) => onChange({ ...node, sql })}
        envVarNames={envVarNames}
        driverCaps={driverCaps}
        onPreflight={onSqlPreflight && node.sql ? () => onSqlPreflight(node.sql!) : undefined}
        preflightBusy={preflightBusy}
      />
    );
  }

  if (node.type === "grpc") {
    return (
      <GrpcNodeEditor
        c={c}
        grpc={node.grpc ?? { extractors: [] }}
        onChange={(grpc) => onChange({ ...node, grpc })}
        driverCaps={driverCaps}
      />
    );
  }

  if (node.type === "if") {
    return (
      <div>
        <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: c.primary }}>Si</span>
          <ConditionEditor c={c} condition={node.condition ?? { kind: "always" }} onChange={(cond) => onChange({ ...node, condition: cond })} />
        </div>
        <BranchBlock c={c} label="Entonces">
          <NodeListEditor
            c={c}
            scenarios={scenarios}
            nodes={node.then ?? []}
            depth={depth + 1}
            onChange={(nodes) => onChange({ ...node, then: nodes })}
            envVarNames={envVarNames}
            driverCaps={driverCaps}
            onSqlPreflight={onSqlPreflight}
            preflightBusy={preflightBusy}
          />
        </BranchBlock>
        <BranchBlock c={c} label="Si no (opcional)">
          <NodeListEditor
            c={c}
            scenarios={scenarios}
            nodes={node.else ?? []}
            depth={depth + 1}
            onChange={(nodes) => onChange({ ...node, else: nodes })}
            envVarNames={envVarNames}
            driverCaps={driverCaps}
            onSqlPreflight={onSqlPreflight}
            preflightBusy={preflightBusy}
          />
        </BranchBlock>
      </div>
    );
  }

  const isWhile = node.mode === "while";
  return (
    <div>
      <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 8, flexWrap: "wrap" }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: c.primary }}>Bucle</span>
        <select
          value={node.mode ?? "count"}
          onChange={(e) => onChange({ ...node, mode: e.target.value as "count" | "while" })}
          style={apiInputStyle(c, { width: 130 })}
        >
          <option value="count">Repetir N veces</option>
          <option value="while">Mientras (while)</option>
        </select>
        {isWhile ? (
          <ConditionEditor c={c} condition={node.condition ?? { kind: "always" }} onChange={(cond) => onChange({ ...node, condition: cond })} />
        ) : (
          <input
            value={node.count ?? ""}
            onChange={(e) => onChange({ ...node, count: e.target.value })}
            placeholder="N o {{var}}"
            style={apiInputStyle(c, { width: 110 })}
          />
        )}
        <label style={{ fontSize: 12, color: c.muted, display: "flex", alignItems: "center", gap: 4 }}>
          máx
          <input
            type="number"
            min={1}
            value={node.max_iterations ?? 100}
            onChange={(e) => onChange({ ...node, max_iterations: Number(e.target.value) || 100 })}
            style={apiInputStyle(c, { width: 70 })}
          />
        </label>
      </div>
      <BranchBlock c={c} label="Cuerpo del bucle">
        <NodeListEditor
          c={c}
          scenarios={scenarios}
          nodes={node.body ?? []}
          depth={depth + 1}
          onChange={(nodes) => onChange({ ...node, body: nodes })}
          envVarNames={envVarNames}
          driverCaps={driverCaps}
          onSqlPreflight={onSqlPreflight}
          preflightBusy={preflightBusy}
        />
      </BranchBlock>
    </div>
  );
}

function BranchBlock(props: { c: Theme; label: string; children: React.ReactNode }) {
  const { c, label, children } = props;
  return (
    <div style={{ borderLeft: `2px solid ${c.border}`, paddingLeft: 12, marginLeft: 4, marginBottom: 8 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5, color: c.muted, marginBottom: 6 }}>
        {label}
      </div>
      {children}
    </div>
  );
}

export function NodeListEditor(props: {
  c: Theme;
  scenarios: { id: string; name: string }[];
  nodes: FlowNode[];
  depth: number;
  onChange: (nodes: FlowNode[]) => void;
  envVarNames?: string[];
  driverCaps?: DriverCapabilities | null;
  onSqlPreflight?: (sql: SqlConfig) => void;
  preflightBusy?: boolean;
}) {
  const { c, scenarios, nodes, depth, onChange, envVarNames, driverCaps, onSqlPreflight, preflightBusy } = props;
  const firstScenario = scenarios[0]?.id ?? "";

  const addNode = (type: FlowNode["type"]) => {
    onChange([...nodes, defaultNode(type, firstScenario)]);
  };
  const updateAt = (idx: number, node: FlowNode) => {
    const next = [...nodes];
    next[idx] = node;
    onChange(next);
  };
  const removeAt = (idx: number) => onChange(nodes.filter((_, i) => i !== idx));
  const move = (idx: number, dir: -1 | 1) => {
    const target = idx + dir;
    if (target < 0 || target >= nodes.length) return;
    const next = [...nodes];
    [next[idx], next[target]] = [next[target], next[idx]];
    onChange(next);
  };

  return (
    <div>
      {nodes.map((node, idx) => (
        <div
          key={idx}
          style={{
            border: `1px solid ${c.border}`,
            borderRadius: 8,
            padding: 10,
            marginBottom: 8,
            background: c.surface,
          }}
        >
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 4, marginBottom: 6 }}>
            <button type="button" title="Subir" onClick={() => move(idx, -1)} style={apiBtn(c, undefined, undefined, true)}>
              ↑
            </button>
            <button type="button" title="Bajar" onClick={() => move(idx, 1)} style={apiBtn(c, undefined, undefined, true)}>
              ↓
            </button>
            <button type="button" title="Eliminar" onClick={() => removeAt(idx)} style={apiBtn(c, undefined, undefined, true)}>
              ✕
            </button>
          </div>
          <NodeEditor
            c={c}
            scenarios={scenarios}
            node={node}
            depth={depth}
            onChange={(n) => updateAt(idx, n)}
            envVarNames={envVarNames}
            driverCaps={driverCaps}
            onSqlPreflight={onSqlPreflight}
            preflightBusy={preflightBusy}
          />
        </div>
      ))}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <button type="button" onClick={() => addNode("request")} style={apiBtn(c, undefined, undefined, true)}>
          + Petición
        </button>
        <button type="button" onClick={() => addNode("if")} style={apiBtn(c, undefined, undefined, true)}>
          + Condición (If)
        </button>
        <button type="button" onClick={() => addNode("loop")} style={apiBtn(c, undefined, undefined, true)}>
          + Bucle (Loop/While)
        </button>
        <button type="button" onClick={() => addNode("sql")} style={apiBtn(c, undefined, undefined, true)}>
          + SQL
        </button>
        <button type="button" onClick={() => addNode("grpc")} style={apiBtn(c, undefined, undefined, true)}>
          + gRPC
        </button>
      </div>
    </div>
  );
}
