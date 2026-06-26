import React, { useEffect, useState } from "react";
import { getApiDataFiles, getLoadTestProfiles } from "../../api";
import { apiBtn, apiInputStyle } from "./apiUi";

export type LoadTestSettings = {
  profile: string;
  thinkTimeMode: "profile" | "between" | "constant" | "none";
  thinkMin: string;
  thinkMax: string;
  thinkValue: string;
  slaEnabled: boolean;
  slaP95: string;
  slaErrorPct: string;
  slaMinRps: string;
  dataFile: string;
  mode: "standalone" | "master" | "worker";
  masterHost: string;
  masterPort: string;
  expectWorkers: string;
  processes: string;
};

export const defaultLoadTestSettings: LoadTestSettings = {
  profile: "load",
  thinkTimeMode: "profile",
  thinkMin: "0.5",
  thinkMax: "2",
  thinkValue: "1",
  slaEnabled: false,
  slaP95: "500",
  slaErrorPct: "1",
  slaMinRps: "",
  dataFile: "",
  mode: "standalone",
  masterHost: "",
  masterPort: "5557",
  expectWorkers: "1",
  processes: "0",
};

type Props = {
  c: Record<string, string>;
  project: string;
  settings: LoadTestSettings;
  onChange: (patch: Partial<LoadTestSettings>) => void;
  onPreflight?: () => void;
  preflightBusy?: boolean;
};

export function buildThinkTimePayload(settings: LoadTestSettings): Record<string, unknown> | undefined {
  if (settings.thinkTimeMode === "none" || settings.thinkTimeMode === "profile") return undefined;
  if (settings.thinkTimeMode === "between") {
    return {
      kind: "between",
      min: Number(settings.thinkMin) || 0.5,
      max: Number(settings.thinkMax) || 2,
    };
  }
  return { kind: "constant", value: Number(settings.thinkValue) || 1 };
}

export function validateDistributedLoadSettings(settings: LoadTestSettings): string | null {
  if (settings.mode === "worker") {
    if (!settings.masterHost.trim()) {
      return "Modo worker: indica la IP o hostname del master.";
    }
    if (!Number(settings.masterPort)) {
      return "Modo worker: indica el puerto del master (por defecto 5557).";
    }
  }
  if (settings.mode !== "standalone" && Number(settings.processes)) {
    return "No combines procesos Locust locales con modo master/worker en red.";
  }
  return null;
}

export function buildSlaPayload(settings: LoadTestSettings): Record<string, unknown> | undefined {
  if (!settings.slaEnabled) return undefined;
  const sla: Record<string, unknown> = {};
  if (settings.slaP95.trim()) sla.max_p95_ms = Number(settings.slaP95);
  if (settings.slaErrorPct.trim()) sla.max_error_pct = Number(settings.slaErrorPct);
  if (settings.slaMinRps.trim()) sla.min_rps = Number(settings.slaMinRps);
  return Object.keys(sla).length ? sla : undefined;
}

export function LoadTestPanel(props: Props) {
  const { c, project, settings, onChange, onPreflight, preflightBusy = false } = props;
  const [profiles, setProfiles] = useState<{ id: string; label: string }[]>([]);
  const [dataFiles, setDataFiles] = useState<string[]>([]);

  useEffect(() => {
    void getLoadTestProfiles()
      .then((r) => setProfiles(r.profiles || []))
      .catch(() =>
        setProfiles([
          { id: "load", label: "Carga sostenida" },
          { id: "stress", label: "Estrés (rampa hasta techo)" },
          { id: "spike", label: "Spike (pico abrupto)" },
          { id: "soak", label: "Soak / resistencia" },
          { id: "scalability", label: "Escalabilidad por escalones" },
          { id: "volume", label: "Volumen (carga + CSV)" },
        ]),
      );
  }, []);

  useEffect(() => {
    if (!project.trim()) return;
    void getApiDataFiles(project)
      .then((r) => setDataFiles((r.files || []).map((f) => f.name)))
      .catch(() => setDataFiles([]));
  }, [project]);

  const profileHelp: Record<string, string> = {
    load: "Carga plana con think-time moderado.",
    stress: "Cuatro escalones hasta el 100 % de usuarios configurados.",
    spike: "Pico abrupto y vuelta a línea base.",
    soak: "70 % de usuarios durante toda la duración.",
    scalability: "Cinco escalones progresivos (informe con tabla de escalones).",
    volume: "Ideal con CSV: cada usuario rota filas del archivo de datos.",
  };

  return (
    <div
      data-testid="elia-load-test-panel"
      style={{
        display: "grid",
        gap: 12,
        marginBottom: 10,
        padding: 12,
        borderRadius: 10,
        border: `1px solid ${c.border}`,
        background: c.neutralBg,
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 13 }}>Plantilla de carga</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div style={{ flex: "1 1 220px" }}>
          <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Perfil</label>
          <select
            value={settings.profile}
            onChange={(e) => onChange({ profile: e.target.value })}
            style={apiInputStyle(c, { width: "100%" })}
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </div>
        <div style={{ flex: "2 1 280px", fontSize: 12, color: c.muted, lineHeight: 1.4 }}>
          {profileHelp[settings.profile] || ""}
        </div>
      </div>

      <div>
        <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 6 }}>Think-time</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select
            value={settings.thinkTimeMode}
            onChange={(e) => onChange({ thinkTimeMode: e.target.value as LoadTestSettings["thinkTimeMode"] })}
            style={apiInputStyle(c, { minWidth: 180 })}
          >
            <option value="profile">Según plantilla</option>
            <option value="between">Aleatorio (min–max s)</option>
            <option value="constant">Constante (s)</option>
            <option value="none">Sin pausa</option>
          </select>
          {settings.thinkTimeMode === "between" ? (
            <>
              <input
                value={settings.thinkMin}
                onChange={(e) => onChange({ thinkMin: e.target.value })}
                placeholder="min"
                style={apiInputStyle(c, { width: 64 })}
              />
              <span style={{ fontSize: 12, color: c.muted }}>–</span>
              <input
                value={settings.thinkMax}
                onChange={(e) => onChange({ thinkMax: e.target.value })}
                placeholder="max"
                style={apiInputStyle(c, { width: 64 })}
              />
            </>
          ) : null}
          {settings.thinkTimeMode === "constant" ? (
            <input
              value={settings.thinkValue}
              onChange={(e) => onChange({ thinkValue: e.target.value })}
              placeholder="segundos"
              style={apiInputStyle(c, { width: 80 })}
            />
          ) : null}
        </div>
      </div>

      <div>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, marginBottom: 6 }}>
          <input
            type="checkbox"
            checked={settings.slaEnabled}
            onChange={(e) => onChange({ slaEnabled: e.target.checked })}
          />
          Evaluar SLA al finalizar (PASS/FAIL en panel de métricas)
        </label>
        {settings.slaEnabled ? (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <div>
              <label style={{ display: "block", fontSize: 11, color: c.muted }}>p95 máx (ms)</label>
              <input
                value={settings.slaP95}
                onChange={(e) => onChange({ slaP95: e.target.value })}
                style={apiInputStyle(c, { width: 88 })}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, color: c.muted }}>Error máx (%)</label>
              <input
                value={settings.slaErrorPct}
                onChange={(e) => onChange({ slaErrorPct: e.target.value })}
                style={apiInputStyle(c, { width: 72 })}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, color: c.muted }}>RPS mín</label>
              <input
                value={settings.slaMinRps}
                onChange={(e) => onChange({ slaMinRps: e.target.value })}
                placeholder="opcional"
                style={apiInputStyle(c, { width: 72 })}
              />
            </div>
          </div>
        ) : null}
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
        <div style={{ flex: "1 1 200px" }}>
          <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>
            CSV de datos (correlación bajo carga)
          </label>
          <select
            value={settings.dataFile}
            onChange={(e) => onChange({ dataFile: e.target.value })}
            style={apiInputStyle(c, { width: "100%" })}
          >
            <option value="">— sin CSV —</option>
            {dataFiles.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Procesos Locust</label>
          <input
            value={settings.processes}
            onChange={(e) => onChange({ processes: e.target.value })}
            title="0 = un proceso; -1 = todos los núcleos"
            style={apiInputStyle(c, { width: 72 })}
          />
        </div>
      </div>

      <div>
        <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 6 }}>Modo distribuido (opcional)</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          <select
            value={settings.mode}
            onChange={(e) => onChange({ mode: e.target.value as LoadTestSettings["mode"] })}
            style={apiInputStyle(c, { minWidth: 140 })}
          >
            <option value="standalone">Standalone (local)</option>
            <option value="master">Master</option>
            <option value="worker">Worker</option>
          </select>
          {settings.mode !== "standalone" ? (
            <>
              <input
                value={settings.masterHost}
                onChange={(e) => onChange({ masterHost: e.target.value })}
                placeholder="Host master"
                style={apiInputStyle(c, { minWidth: 140 })}
              />
              <input
                value={settings.masterPort}
                onChange={(e) => onChange({ masterPort: e.target.value })}
                placeholder="Puerto"
                style={apiInputStyle(c, { width: 72 })}
              />
            </>
          ) : null}
          {settings.mode === "master" ? (
            <input
              value={settings.expectWorkers}
              onChange={(e) => onChange({ expectWorkers: e.target.value })}
              placeholder="Workers esperados"
              style={apiInputStyle(c, { width: 120 })}
            />
          ) : null}
          {onPreflight && settings.mode !== "standalone" ? (
            <button type="button" disabled={preflightBusy} onClick={onPreflight} style={apiBtn(c, undefined, undefined, true)}>
              {preflightBusy ? "Comprobando…" : "Preflight red"}
            </button>
          ) : null}
        </div>
        {settings.mode !== "standalone" ? (
          <div
            style={{
              marginTop: 8,
              padding: 10,
              borderRadius: 8,
              border: `1px solid ${c.border}`,
              fontSize: 11,
              color: c.muted,
              lineHeight: 1.5,
            }}
          >
            <strong style={{ color: c.text }}>Carga distribuida (ELIA Architect)</strong>
            <ol style={{ margin: "6px 0 0", paddingLeft: 18 }}>
              <li>
                <strong>Master</strong> en la máquina coordinadora: mismo proyecto API, flujo/escenarios y parámetros
                (-u/-r/-t). Puerto por defecto 5557.
              </li>
              <li>
                <strong>Worker</strong> en cada nodo generador: mismo proyecto y locustfile (ELIA lo regenera al
                lanzar). Indica IP del master; no configures usuarios aquí.
              </li>
              <li>Firewall: permite TCP entre workers y master (puerto master).</li>
              <li>No uses «Procesos Locust» junto con master/worker en red.</li>
            </ol>
          </div>
        ) : null}
      </div>
    </div>
  );
}
