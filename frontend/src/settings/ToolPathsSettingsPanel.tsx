import React from "react";
import {
  getToolPathsStatus,
  pickDirectory,
  pickExecutable,
  postToolPathsDiagnostic,
  putToolPaths,
  testToolPath,
  type ToolPathEntryStatus,
  type ToolPathsStatusResponse,
} from "../api";
import { LoadingStatusRow } from "../components/LoadingStatusRow";
import { EliaButton } from "../components/ui";
import { truncatePathForDisplay } from "../mobileEnvUi";

const GROUPS: { id: string; label: string; keys: readonly string[] }[] = [
  {
    id: "android",
    label: "Android / Móvil",
    keys: ["android_studio", "android_sdk", "adb", "emulator", "appium"],
  },
  {
    id: "web",
    label: "Web / Chrome",
    keys: ["chrome"],
  },
];

type Props = {
  c: Record<string, string>;
};

function PathField(props: {
  c: Record<string, string>;
  pathKey: string;
  entry: ToolPathEntryStatus;
  value: string;
  onChange: (value: string) => void;
  onBrowse: () => void;
  onTest: () => void;
  onClear: () => void;
}) {
  const { c, pathKey, entry, value, onChange, onBrowse, onTest, onClear } = props;
  return (
    <div
      data-testid={`elia-tool-path-${pathKey}`}
      style={{
        border: `1px solid ${c.border}`,
        borderRadius: 10,
        padding: 10,
        background: c.inputBg,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 6 }}>
        <div style={{ fontWeight: 700, fontSize: 13, color: c.text }}>{entry.label}</div>
        <div style={{ fontSize: 11, color: entry.ok ? c.muted : c.errorTitle }}>
          {entry.effective ? entry.message : "No detectado"}
        </div>
      </div>
      {entry.detected ? (
        <div style={{ fontSize: 11, color: c.muted, marginBottom: 6, lineHeight: 1.45 }}>
          Auto: {truncatePathForDisplay(entry.detected)}
          {entry.detected_source ? ` (${entry.detected_source})` : ""}
        </div>
      ) : null}
      {entry.effective && entry.override ? (
        <div style={{ fontSize: 11, color: c.muted, marginBottom: 6 }}>
          Activo: {truncatePathForDisplay(String(entry.effective))} ({entry.effective_source})
        </div>
      ) : null}
      <input
        className="elia-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={entry.kind === "dir" ? "Carpeta…" : "Ruta al ejecutable…"}
        style={{ width: "100%", marginBottom: 8, fontSize: 13 }}
      />
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <EliaButton variant="ghost" size="sm" onClick={onBrowse}>
          Buscar…
        </EliaButton>
        <EliaButton variant="ghost" size="sm" onClick={onTest}>
          Probar
        </EliaButton>
        <EliaButton variant="ghost" size="sm" onClick={onClear}>
          Limpiar
        </EliaButton>
      </div>
    </div>
  );
}

export function ToolPathsSettingsPanel(props: Props) {
  const { c } = props;
  const [status, setStatus] = React.useState<ToolPathsStatusResponse | null>(null);
  const [draft, setDraft] = React.useState<Record<string, string>>({});
  const [openGroups, setOpenGroups] = React.useState<Record<string, boolean>>({
    android: true,
    web: true,
  });
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [diagnosticBusy, setDiagnosticBusy] = React.useState(false);
  const [msg, setMsg] = React.useState<string | null>(null);
  const [testMsg, setTestMsg] = React.useState<string | null>(null);
  const [diagnosticMsg, setDiagnosticMsg] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await getToolPathsStatus();
      setStatus(data);
      const next: Record<string, string> = {};
      for (const group of GROUPS) {
        for (const key of group.keys) {
          next[key] = data.paths[key]?.override ?? "";
        }
      }
      setDraft(next);
    } catch (e: unknown) {
      setMsg(String((e as Error)?.message ?? e));
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleSave = () => {
    setSaving(true);
    setMsg(null);
    void (async () => {
      try {
        const payload: Record<string, string | null> = {};
        for (const group of GROUPS) {
          for (const key of group.keys) {
            const val = (draft[key] ?? "").trim();
            payload[key] = val || null;
          }
        }
        const data = await putToolPaths(payload);
        setStatus(data);
        setMsg("Rutas guardadas.");
      } catch (e: unknown) {
        setMsg(String((e as Error)?.message ?? e));
      } finally {
        setSaving(false);
      }
    })();
  };

  const handleBrowse = (key: string, entry: ToolPathEntryStatus) => {
    void (async () => {
      try {
        const res =
          entry.kind === "dir"
            ? await pickDirectory(entry.label)
            : await pickExecutable(entry.label);
        if (res.path) setDraft((prev) => ({ ...prev, [key]: res.path! }));
      } catch (e: unknown) {
        setTestMsg(String((e as Error)?.message ?? e));
      }
    })();
  };

  const handleTest = (key: string) => {
    void (async () => {
      try {
        const res = await testToolPath(key, draft[key]?.trim() || undefined);
        setTestMsg(res.ok ? `✓ ${key}: ${res.message}` : `✗ ${key}: ${res.message}`);
      } catch (e: unknown) {
        setTestMsg(String((e as Error)?.message ?? e));
      }
    })();
  };

  const handleDiagnostic = () => {
    setDiagnosticBusy(true);
    setDiagnosticMsg(null);
    void (async () => {
      try {
        const res = await postToolPathsDiagnostic();
        const mobileOk = res.mobile?.ok ? "✓ Móvil" : "✗ Móvil";
        const chromeOk = res.chrome?.ok ? "✓ Chrome" : "✗ Chrome";
        const pathsOk = res.tool_paths?.paths
          ? Object.values(res.tool_paths.paths).filter((p) => p.effective && !p.ok).length === 0
            ? "✓ Rutas"
            : "⚠ Rutas"
          : "";
        setDiagnosticMsg(`${mobileOk} · ${chromeOk} · ${pathsOk}`.trim());
        if (res.tool_paths) setStatus(res.tool_paths);
      } catch (e: unknown) {
        setDiagnosticMsg(String((e as Error)?.message ?? e));
      } finally {
        setDiagnosticBusy(false);
      }
    })();
  };

  if (loading) {
    return (
      <LoadingStatusRow
        c={c}
        text="Cargando entorno local…"
        loading
        testId="elia-tool-paths-loading"
      />
    );
  }

  return (
    <div data-testid="elia-tool-paths-settings">
      <div style={{ fontWeight: 800, marginBottom: 6 }}>Entorno local</div>
      <div style={{ color: c.muted, fontSize: 13, marginBottom: 14, lineHeight: 1.55 }}>
        Rutas de herramientas en esta máquina. Si dejas un campo vacío, ELIA intenta detectarlas
        automáticamente (incluye JetBrains Toolbox y PATH). Se guardan en{" "}
        <code style={{ fontSize: 12 }}>{status?.config_file ?? "Documents/ELIA/tool_paths.json"}</code>.
      </div>

      <div style={{ marginBottom: 14 }}>
        <EliaButton
          variant="ghost"
          size="sm"
          data-testid="elia-tool-paths-diagnostic"
          disabled={diagnosticBusy}
          onClick={handleDiagnostic}
        >
          {diagnosticBusy ? "Diagnosticando…" : "Ejecutar diagnóstico"}
        </EliaButton>
        {diagnosticMsg ? (
          <div style={{ fontSize: 12, color: c.muted, marginTop: 8 }}>{diagnosticMsg}</div>
        ) : null}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {GROUPS.map((group) => (
          <div
            key={group.id}
            style={{
              border: `1px solid ${c.border}`,
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <button
              type="button"
              onClick={() => setOpenGroups((prev) => ({ ...prev, [group.id]: !prev[group.id] }))}
              style={{
                width: "100%",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "10px 12px",
                border: "none",
                background: c.neutralBg,
                color: c.text,
                cursor: "pointer",
                fontWeight: 700,
                fontSize: 13,
              }}
            >
              <span>{group.label}</span>
              <span>{openGroups[group.id] ? "▾" : "▸"}</span>
            </button>
            {openGroups[group.id] ? (
              <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
                {group.keys.map((key) => {
                  const entry = status?.paths[key];
                  if (!entry) return null;
                  return (
                    <PathField
                      key={key}
                      c={c}
                      pathKey={key}
                      entry={entry}
                      value={draft[key] ?? ""}
                      onChange={(value) => setDraft((prev) => ({ ...prev, [key]: value }))}
                      onBrowse={() => handleBrowse(key, entry)}
                      onTest={() => handleTest(key)}
                      onClear={() => setDraft((prev) => ({ ...prev, [key]: "" }))}
                    />
                  );
                })}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {testMsg ? <div style={{ fontSize: 12, color: c.muted, marginTop: 12 }}>{testMsg}</div> : null}
      {msg ? <div style={{ fontSize: 12, color: c.text, marginTop: 8 }}>{msg}</div> : null}

      <div style={{ display: "flex", gap: 10, marginTop: 16, justifyContent: "flex-end" }}>
        <EliaButton variant="ghost" size="sm" onClick={() => void refresh()}>
          Recargar
        </EliaButton>
        <EliaButton variant="primary" size="sm" data-testid="elia-tool-paths-save" disabled={saving} onClick={handleSave}>
          {saving ? "Guardando…" : "Guardar rutas"}
        </EliaButton>
      </div>
    </div>
  );
}
