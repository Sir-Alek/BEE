import React, { useEffect, useMemo, useState } from "react";
import type { ConversionResultPayload, GeneratedFileEntry } from "../types";

function normalizeGeneratedFiles(
  payload?: ConversionResultPayload | null,
  progress?: Record<string, unknown>,
): { dir?: string; files: GeneratedFileEntry[] } {
  const dir =
    payload?.output_dir ||
    payload?.project_dir ||
    progress?.output_dir ||
    progress?.project_dir;
  let files: GeneratedFileEntry[] = payload?.generated_files ?? [];
  if (!files.length && Array.isArray(progress?.generated_files)) {
    files = progress.generated_files as GeneratedFileEntry[];
  }
  if (!files.length && progress?.result_file) {
    files = [{ path: String(progress.result_file), label: "grabación" }];
  }
  if (!files.length && progress?.video_path) {
    files = [{ path: String(progress.video_path), label: "video" }];
  }
  return { dir: dir ? String(dir) : undefined, files };
}

export function GeneratedFilesResultView(props: {
  message?: string;
  payload?: ConversionResultPayload | null;
  progress?: Record<string, unknown>;
  c: Record<string, string>;
}) {
  const { message, payload, progress, c } = props;
  const { dir, files } = normalizeGeneratedFiles(payload, progress);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {message ? (
        <div style={{ whiteSpace: "pre-wrap", fontSize: 14 }}>{message}</div>
      ) : null}
      {dir ? (
        <div style={{ fontSize: 13 }}>
          <div style={{ color: c.muted, marginBottom: 4 }}>Carpeta de salida</div>
          <code
            style={{
              display: "block",
              padding: "8px 10px",
              borderRadius: 8,
              background: c.codeBg,
              border: `1px solid ${c.border}`,
              fontSize: 12,
              wordBreak: "break-all",
            }}
          >
            {dir}
          </code>
        </div>
      ) : null}
      {files.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 13, color: c.muted }}>Archivos generados</div>
          {files.map((f) => (
            <div
              key={f.path}
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 10,
                padding: 10,
                background: c.surface,
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 13, color: c.text }}>
                {f.label || f.path.split(/[/\\]/).pop()}
              </div>
              <code
                style={{
                  display: "block",
                  marginTop: 4,
                  fontSize: 11,
                  color: c.muted,
                  wordBreak: "break-all",
                }}
              >
                {f.path}
              </code>
              {f.preview ? (
                <textarea
                  readOnly
                  value={f.preview}
                  style={{
                    width: "100%",
                    minHeight: 120,
                    marginTop: 8,
                    padding: 8,
                    borderRadius: 8,
                    border: `1px solid ${c.border}`,
                    fontFamily: "ui-monospace, monospace",
                    fontSize: 12,
                    background: c.codeBg,
                    color: c.text,
                    resize: "vertical",
                  }}
                />
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function ActionsCheckboxList(props: {
  c: Record<string, string>;
  promptId?: string;
  actions: { type: string; description: string; original_line: string }[];
  minSelected?: number;
  emptySelectionMessage?: string;
  onSubmit: (selectedLines: string[]) => void | Promise<void>;
}) {
  const { c } = props;
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [emptyHint, setEmptyHint] = useState(false);
  const minSelected = props.minSelected ?? 1;

  const actionsFingerprint = props.actions
    .map((a) => a.original_line)
    .sort()
    .join("\0");

  useEffect(() => {
    setEmptyHint(false);
    setSelected((prev) => {
      const next: Record<string, boolean> = {};
      for (const a of props.actions) {
        next[a.original_line] = prev[a.original_line] ?? true;
      }
      return next;
    });
  }, [props.promptId, actionsFingerprint]);

  const selectedLines = useMemo(() => {
    return props.actions.filter((a) => selected[a.original_line]).map((a) => a.original_line);
  }, [props.actions, selected]);

  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {props.actions.map((a, idx) => (
          <label key={idx} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <input
              type="checkbox"
              checked={!!selected[a.original_line]}
              onChange={(e) => setSelected((prev) => ({ ...prev, [a.original_line]: e.target.checked }))}
              style={{ marginTop: 3 }}
            />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: c.text }}>{a.type}</div>
              <div style={{ fontSize: 12, color: c.actionDesc }}>{a.description}</div>
            </div>
          </label>
        ))}
      </div>

      {emptyHint ? (
        <div style={{ marginTop: 10, fontSize: 13, color: c.errorTitle }}>
          {props.emptySelectionMessage ??
            "Selecciona al menos una acción para continuar."}
        </div>
      ) : null}

      <div style={{ display: "flex", gap: 10, marginTop: 14, justifyContent: "flex-end" }}>
        <button
          onClick={() => setSelected((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, true])))}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            background: c.btnGhostBg,
            border: `1px solid ${c.btnGhostBorder}`,
            color: c.text,
            cursor: "pointer",
          }}
        >
          Incluir todas
        </button>
        <button
          onClick={() => setSelected((prev) => Object.fromEntries(Object.keys(prev).map((k) => [k, false])))}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            background: c.btnGhostBg,
            border: `1px solid ${c.btnGhostBorder}`,
            color: c.text,
            cursor: "pointer",
          }}
        >
          Excluir todas
        </button>
        <button
          onClick={() => {
            if (selectedLines.length < minSelected) {
              setEmptyHint(true);
              return;
            }
            void props.onSubmit(selectedLines);
          }}
          style={{
            padding: "8px 12px",
            borderRadius: 10,
            background: c.primary,
            color: c.primaryFg,
            border: "none",
            cursor: "pointer",
          }}
        >
          Continuar
        </button>
      </div>
    </div>
  );
}
