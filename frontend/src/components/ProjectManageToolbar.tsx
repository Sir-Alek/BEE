import React from "react";
import {
  deleteProject,
  getProjectInfo,
  openProjectFolder,
  renameProject,
  type ProjectInfoResponse,
} from "../api";
import { FOLDER_OPEN_HINT } from "../app/folderOpenHint";
import { useAutoDismissHint } from "../hooks/useAutoDismissHint";
import { InlineActionHint } from "./InlineActionHint";

type Props = {
  c: Record<string, string>;
  platform: "web" | "mobile" | "legacy" | "api";
  project: string;
  disabled?: boolean;
  onProjectRenamed: (newName: string) => void;
  onProjectDeleted: () => void;
  onError: (msg: string) => void;
};

function ghostBtn(c: Record<string, string>, danger = false): React.CSSProperties {
  return {
    padding: "6px 10px",
    borderRadius: 8,
    border: `1px solid ${danger ? (c.dangerBtnBorder ?? c.errorBorder ?? "#c0392b") : c.btnGhostBorder}`,
    background: danger ? (c.dangerBtnBg ?? c.errorBg ?? "rgba(192,57,43,0.08)") : c.btnGhostBg,
    color: danger ? (c.dangerBtnText ?? c.errorTitle ?? "#c0392b") : c.text,
    fontWeight: 600,
    fontSize: 12,
    cursor: "pointer",
  };
}

export function ProjectManageToolbar(props: Props) {
  const { c, platform, project, disabled, onProjectRenamed, onProjectDeleted, onError } = props;
  const [info, setInfo] = React.useState<ProjectInfoResponse | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [renameOpen, setRenameOpen] = React.useState(false);
  const [renameValue, setRenameValue] = React.useState("");
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [deleteConfirm, setDeleteConfirm] = React.useState("");
  const [folderHint, setFolderHint] = useAutoDismissHint();

  React.useEffect(() => {
    if (!project.trim()) {
      setInfo(null);
      return;
    }
    let cancelled = false;
    void getProjectInfo(platform, project)
      .then((r) => {
        if (!cancelled) setInfo(r);
      })
      .catch(() => {
        if (!cancelled) setInfo(null);
      });
    return () => {
      cancelled = true;
    };
  }, [platform, project]);

  if (!project.trim()) return null;

  const handleOpenRoot = () => {
    setBusy(true);
    void openProjectFolder(platform, project, ".")
      .then((r) => {
        setFolderHint(r.hint ?? FOLDER_OPEN_HINT);
      })
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleRename = () => {
    const next = renameValue.trim();
    if (!next || next === project) {
      setRenameOpen(false);
      return;
    }
    setBusy(true);
    void renameProject(platform, project, next)
      .then((r) => {
        setRenameOpen(false);
        onProjectRenamed(r.project);
      })
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleDelete = () => {
    if (deleteConfirm.trim() !== project) return;
    setBusy(true);
    void deleteProject(platform, project)
      .then(() => {
        setDeleteOpen(false);
        setDeleteConfirm("");
        onProjectDeleted();
      })
      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  return (
    <>
      <div style={{ marginBottom: 10 }}>
        <div
          data-testid={`elia-project-manage-${platform}`}
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            alignItems: "center",
          }}
        >
          {info?.from_template && info.template_id ? (
            <span
              data-testid="elia-project-template-badge"
              style={{
                fontSize: 11,
                fontWeight: 700,
                padding: "4px 8px",
                borderRadius: 999,
                background: c.hintBg,
                border: `1px solid ${c.hintBorder}`,
                color: c.hintText,
              }}
            >
              Plantilla: {info.template_id}
            </span>
          ) : null}
          <button
            type="button"
            disabled={disabled || busy}
            onClick={handleOpenRoot}
            style={ghostBtn(c)}
            data-testid="elia-project-open-folder"
          >
            Abrir carpeta
          </button>
          <button
            type="button"
            disabled={disabled || busy}
            onClick={() => {
              setRenameValue(project);
              setRenameOpen(true);
            }}
            style={ghostBtn(c)}
            data-testid="elia-project-rename"
          >
            Renombrar
          </button>
          <button
            type="button"
            disabled={disabled || busy}
            onClick={() => {
              setDeleteConfirm("");
              setDeleteOpen(true);
            }}
            style={ghostBtn(c, true)}
            data-testid="elia-project-delete"
          >
            Eliminar proyecto
          </button>
        </div>
        <InlineActionHint c={c} message={folderHint} testId="elia-project-open-folder-hint" />
      </div>

      {renameOpen ? (
        <div
          data-testid="elia-project-rename-modal"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1100,
            padding: 16,
          }}
          onClick={() => setRenameOpen(false)}
        >
          <div
            style={{
              background: c.surface,
              border: `1px solid ${c.border}`,
              borderRadius: 14,
              padding: 20,
              width: "min(420px, 96vw)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ fontWeight: 800, marginBottom: 8, color: c.text }}>Renombrar proyecto</div>
            <div style={{ fontSize: 13, color: c.muted, marginBottom: 12 }}>
              Nuevo nombre en behave/{platform}/ (solo letras, números, guiones).
            </div>
            <input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 10,
                border: `1px solid ${c.inputBorder}`,
                background: c.inputBg,
                color: c.text,
                marginBottom: 14,
              }}
              data-testid="elia-project-rename-input"
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button type="button" onClick={() => setRenameOpen(false)} style={ghostBtn(c)}>
                Cancelar
              </button>
              <button
                type="button"
                disabled={busy || !renameValue.trim() || renameValue.trim() === project}
                onClick={handleRename}
                style={{ ...ghostBtn(c), background: c.primary, color: "#fff", border: "none" }}
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {deleteOpen ? (
        <div
          data-testid="elia-project-delete-modal"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1100,
            padding: 16,
          }}
          onClick={() => setDeleteOpen(false)}
        >
          <div
            style={{
              background: c.surface,
              border: `1px solid ${c.errorBorder ?? c.border}`,
              borderRadius: 14,
              padding: 20,
              width: "min(460px, 96vw)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ fontWeight: 800, marginBottom: 8, color: c.errorTitle ?? c.text }}>
              Eliminar proyecto
            </div>
            <div style={{ fontSize: 13, color: c.text, marginBottom: 12, lineHeight: 1.5 }}>
              Se borrará permanentemente <b>{project}</b> y todo su contenido local (features, evidencias,
              escenarios API). Esta acción no se puede deshacer.
            </div>
            <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>
              Escribe <code>{project}</code> para confirmar:
            </div>
            <input
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 10,
                border: `1px solid ${c.inputBorder}`,
                background: c.inputBg,
                color: c.text,
                marginBottom: 14,
              }}
              data-testid="elia-project-delete-confirm-input"
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button type="button" onClick={() => setDeleteOpen(false)} style={ghostBtn(c)}>
                Cancelar
              </button>
              <button
                type="button"
                disabled={busy || deleteConfirm.trim() !== project}
                onClick={handleDelete}
                style={ghostBtn(c, true)}
              >
                Eliminar definitivamente
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
