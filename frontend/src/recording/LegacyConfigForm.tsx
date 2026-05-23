import React from "react";

export function LegacyConfigForm(props: {
  c: Record<string, string>;
  windowName: string;
  exePath: string;
  onWindowNameChange: (value: string) => void;
  onExePathChange: (value: string) => void;
}) {
  const { c, windowName, exePath, onWindowNameChange, onExePathChange } = props;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 14 }}>
      <input
        value={windowName}
        onChange={(e) => onWindowNameChange(e.target.value)}
        placeholder="Nombre de la ventana (título exacto, ej: Mi Aplicación)"
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          border: `1px solid ${c.inputBorder}`,
          background: c.inputBg,
          color: c.text,
          outline: "none",
          fontSize: 14,
        }}
      />
      <input
        value={exePath}
        onChange={(e) => onExePathChange(e.target.value)}
        placeholder="Ruta del ejecutable .exe (opcional si ya está abierto)"
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          border: `1px solid ${c.inputBorder}`,
          background: c.inputBg,
          color: c.text,
          outline: "none",
          fontSize: 14,
        }}
      />
      <div style={{ fontSize: 12, color: c.muted }}>
        Grabación de interacciones en aplicaciones de escritorio Windows.
      </div>
    </div>
  );
}
