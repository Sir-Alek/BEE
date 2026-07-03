import React from "react";
import { EliaButton } from "./ui";

type Props = {
  c: Record<string, string>;
  /** Valor del atributo accept del input (p. ej. ".csv,.xlsx"). */
  accept: string;
  /** Extensiones permitidas, con punto (p. ej. [".csv", ".xlsx"]). */
  extensions: string[];
  /** Texto visible de formatos (p. ej. ".csv, .xlsx"). */
  acceptLabel: string;
  hintText?: string;
  disabled?: boolean;
  busy?: boolean;
  multiple?: boolean;
  onFiles: (files: File[]) => void;
  onInvalidFiles?: (message: string) => void;
  testId?: string;
};

export function FileDropZone(props: Props) {
  const {
    c,
    accept,
    extensions,
    acceptLabel,
    hintText,
    disabled,
    busy,
    multiple = false,
    onFiles,
    onInvalidFiles,
    testId,
  } = props;
  const [dragOver, setDragOver] = React.useState(false);

  const filterAllowed = (files: File[]) =>
    files.filter((f) => extensions.some((ext) => f.name.toLowerCase().endsWith(ext)));

  const handlePicked = (files: File[]) => {
    const allowed = filterAllowed(files);
    if (!allowed.length) {
      onInvalidFiles?.(`Solo se admiten archivos ${acceptLabel}`);
      return;
    }
    onFiles(allowed);
  };

  const openBrowse = () => {
    if (disabled || busy) return;
    const input = document.createElement("input");
    input.type = "file";
    input.accept = accept;
    input.multiple = multiple;
    input.onchange = () => {
      const files = Array.from(input.files ?? []);
      if (files.length) handlePicked(files);
    };
    input.click();
  };

  const blocked = disabled || busy;

  return (
    <div
      data-testid={testId}
      onDragOver={(e) => {
        e.preventDefault();
        if (!blocked) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        if (blocked) return;
        handlePicked(Array.from(e.dataTransfer.files));
      }}
      style={{
        border: `2px dashed ${dragOver ? c.primary : c.inputBorder}`,
        borderRadius: 12,
        padding: "16px 14px",
        textAlign: "center",
        background: dragOver ? c.hintBg : c.inputBg,
        color: c.muted,
        fontSize: 13,
        marginBottom: 8,
        transition: "border-color 0.15s, background 0.15s",
      }}
    >
      Arrastra tus archivos aquí · <strong>{acceptLabel}</strong>
      <div style={{ marginTop: 8 }}>
        <EliaButton variant="ghost" size="sm" disabled={blocked} onClick={openBrowse}>
          Buscar archivo
        </EliaButton>
      </div>
      {hintText ? (
        <div style={{ fontSize: 11, marginTop: 8, color: c.muted }}>{hintText}</div>
      ) : null}
    </div>
  );
}
