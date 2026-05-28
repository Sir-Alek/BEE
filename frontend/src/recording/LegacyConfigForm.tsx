import React from "react";
import { FieldLabel } from "../components/ui";

export function LegacyConfigForm(props: {
  c: Record<string, string>;
  windowName: string;
  exePath: string;
  onWindowNameChange: (value: string) => void;
  onExePathChange: (value: string) => void;
}) {
  const { c, windowName, exePath, onWindowNameChange, onExePathChange } = props;

  const inputStyle: React.CSSProperties = {
    padding: "10px 12px",
    borderRadius: 10,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    outline: "none",
    fontSize: 14,
    width: "100%",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
      <FieldLabel
        c={c}
        tooltip="Título exacto de la ventana visible en la barra de tareas. ELIA lo usa para enganchar la grabación UI Automation."
      >
        Ventana de la aplicación
      </FieldLabel>
      <input
        data-testid="elia-legacy-window-name"
        value={windowName}
        onChange={(e) => onWindowNameChange(e.target.value)}
        placeholder="ej: Mi Aplicación — Título exacto"
        style={inputStyle}
      />
      <FieldLabel
        c={c}
        tooltip="Opcional si la app ya está abierta. Ruta completa al .exe para que ELIA la lance antes de grabar."
      >
        Ejecutable (opcional)
      </FieldLabel>
      <input
        data-testid="elia-legacy-exe-path"
        value={exePath}
        onChange={(e) => onExePathChange(e.target.value)}
        placeholder="C:\Program Files\App\app.exe"
        style={inputStyle}
      />
    </div>
  );
}
