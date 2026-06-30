import React from "react";
import { openMobileAndroidStudio, pickExecutable } from "../api";

type Props = {
  c: Record<string, string>;
  open: boolean;
  onClose: () => void;
  onOpened?: (message: string) => void;
  onOpenEnvironmentSettings?: () => void;
  sdkOk?: boolean;
};

export function AndroidStudioPathPanel(props: Props) {
  const { c, open, onClose, onOpened, onOpenEnvironmentSettings, sdkOk } = props;
  const [path, setPath] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [searched, setSearched] = React.useState<string[]>([]);

  React.useEffect(() => {
    if (!open) return;
    setPath("");
    setError(null);
    setSearched([]);
  }, [open]);

  if (!open) return null;

  const runOpen = (save: boolean) => {
    if (!path.trim()) {
      setError("Indica la ruta a studio64.exe o a la carpeta de Android Studio.");
      return;
    }
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        const res = await openMobileAndroidStudio({ path: path.trim(), save });
        if (!res.ok) {
          setError(res.message);
          setSearched(res.searched_paths ?? []);
          return;
        }
        onOpened?.(res.message);
        onClose();
      } catch (e: unknown) {
        setError(String((e as Error)?.message ?? e));
      } finally {
        setBusy(false);
      }
    })();
  };

  const handleBrowse = () => {
    setBusy(true);
    void (async () => {
      try {
        const res = await pickExecutable("Android Studio (studio64.exe)");
        if (res.path) setPath(res.path);
        else if (res.message) setError(res.message);
      } catch (e: unknown) {
        setError(String((e as Error)?.message ?? e));
      } finally {
        setBusy(false);
      }
    })();
  };

  return (
    <div
      data-testid="elia-studio-path-panel"
      style={{
        borderRadius: 12,
        border: `1px solid ${c.severityWarnBorder}`,
        background: c.neutralBg,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 700, color: c.text }}>
        Indicar ruta de Android Studio
      </div>
      <div style={{ fontSize: 12, color: c.muted, lineHeight: 1.5 }}>
        ELIA no encontró Studio en las rutas habituales (incluye JetBrains Toolbox y PATH).
        Selecciona <code style={{ fontSize: 11 }}>studio64.exe</code> o pega la carpeta de instalación.
        {sdkOk ? " El SDK Android ya está detectado; solo falta Studio." : null}
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input
          data-testid="elia-studio-path-input"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="C:\...\Android Studio\bin\studio64.exe"
          style={{
            flex: "1 1 220px",
            padding: "8px 10px",
            borderRadius: 8,
            border: `1px solid ${c.inputBorder}`,
            background: c.inputBg,
            color: c.text,
            fontSize: 13,
          }}
        />
        <button
          type="button"
          data-testid="elia-studio-path-browse"
          disabled={busy}
          onClick={handleBrowse}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: `1px solid ${c.inputBorder}`,
            background: c.inputBg,
            color: c.text,
            cursor: busy ? "wait" : "pointer",
            fontSize: 13,
          }}
        >
          Buscar…
        </button>
      </div>
      {searched.length > 0 && (
        <div style={{ fontSize: 11, color: c.muted, lineHeight: 1.45 }}>
          Rutas probadas: {searched.slice(0, 3).join(" · ")}
          {searched.length > 3 ? " …" : ""}
        </div>
      )}
      {error && <div style={{ fontSize: 12, color: c.errorTitle }}>{error}</div>}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
        {onOpenEnvironmentSettings ? (
          <button
            type="button"
            data-testid="elia-studio-open-env-settings"
            onClick={onOpenEnvironmentSettings}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              border: `1px solid ${c.inputBorder}`,
              background: c.inputBg,
              color: c.text,
              cursor: "pointer",
              fontSize: 13,
              marginRight: "auto",
            }}
          >
            Entorno local…
          </button>
        ) : null}
        <button
          type="button"
          onClick={onClose}
          disabled={busy}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: `1px solid ${c.btnGhostBorder}`,
            background: c.btnGhostBg,
            color: c.text,
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          Cancelar
        </button>
        <button
          type="button"
          data-testid="elia-studio-path-open-once"
          disabled={busy}
          onClick={() => runOpen(false)}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: `1px solid ${c.inputBorder}`,
            background: c.inputBg,
            color: c.text,
            cursor: busy ? "wait" : "pointer",
            fontSize: 13,
          }}
        >
          Abrir una vez
        </button>
        <button
          type="button"
          data-testid="elia-studio-path-save-open"
          disabled={busy}
          onClick={() => runOpen(true)}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "none",
            background: c.primary,
            color: c.primaryFg,
            cursor: busy ? "wait" : "pointer",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          {busy ? "Abriendo…" : "Guardar y abrir"}
        </button>
      </div>
    </div>
  );
}
