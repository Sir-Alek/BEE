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
import { EliaButton, EliaModalActions, EliaModalOverlay, EliaModalPanel } from "./ui";

type Props = {
  c: Record<string, string>;
  platform: "web" | "mobile" | "legacy" | "api";
  project: string;
  disabled?: boolean;
  onProjectRenamed: (newName: string) => void;
  onProjectDeleted: () => void;
  onError: (msg: string) => void;
};

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
          <EliaButton
            variant="ghost"
            size="sm"
            disabled={disabled || busy}
            onClick={handleOpenRoot}
            data-testid="elia-project-open-folder"
          >
            Abrir carpeta
          </EliaButton>
          <EliaButton
            variant="ghost"
            size="sm"
            disabled={disabled || busy}
            onClick={() => {
              setRenameValue(project);
              setRenameOpen(true);
            }}
            data-testid="elia-project-rename"
          >
            Renombrar
          </EliaButton>
          <EliaButton
            variant="danger"
            size="sm"
            disabled={disabled || busy}
            onClick={() => {
              setDeleteConfirm("");
              setDeleteOpen(true);
            }}
            data-testid="elia-project-delete"
          >
            Eliminar proyecto
          </EliaButton>
        </div>
        <InlineActionHint c={c} message={folderHint} testId="elia-project-open-folder-hint" />
      </div>

      {renameOpen ? (
        <EliaModalOverlay testId="elia-project-rename-modal" ariaLabel="Renombrar proyecto" onClose={() => setRenameOpen(false)}>
          <EliaModalPanel onClick={(e) => e.stopPropagation()} style={{ width: "min(420px, 96vw)", padding: 20 }}>
            <div style={{ fontWeight: 800, marginBottom: 8, color: c.text }}>Renombrar proyecto</div>
            <div style={{ fontSize: 13, color: c.muted, marginBottom: 12 }}>
              Nuevo nombre en behave/{platform}/ (solo letras, números, guiones).
            </div>
            <input
              className="elia-input"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              style={{ width: "100%", marginBottom: 14 }}
              data-testid="elia-project-rename-input"
            />
            <EliaModalActions>
              <EliaButton variant="ghost" size="sm" onClick={() => setRenameOpen(false)}>
                Cancelar
              </EliaButton>
              <EliaButton
                variant="primary"
                size="sm"
                disabled={busy || !renameValue.trim() || renameValue.trim() === project}
                onClick={handleRename}
              >
                Guardar
              </EliaButton>
            </EliaModalActions>
          </EliaModalPanel>
        </EliaModalOverlay>
      ) : null}

      {deleteOpen ? (
        <EliaModalOverlay testId="elia-project-delete-modal" ariaLabel="Eliminar proyecto" onClose={() => setDeleteOpen(false)}>
          <EliaModalPanel
            onClick={(e) => e.stopPropagation()}
            style={{ width: "min(460px, 96vw)", padding: 20, border: `1px solid ${c.errorBorder ?? c.border}` }}
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
              className="elia-input"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              style={{ width: "100%", marginBottom: 14 }}
              data-testid="elia-project-delete-confirm-input"
            />
            <EliaModalActions>
              <EliaButton variant="ghost" size="sm" onClick={() => setDeleteOpen(false)}>
                Cancelar
              </EliaButton>
              <EliaButton
                variant="danger"
                size="sm"
                disabled={busy || deleteConfirm.trim() !== project}
                onClick={handleDelete}
              >
                Eliminar definitivamente
              </EliaButton>
            </EliaModalActions>
          </EliaModalPanel>
        </EliaModalOverlay>
      ) : null}
    </>
  );
}
