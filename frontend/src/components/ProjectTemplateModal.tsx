import React from "react";
import {
  createProjectFromTemplate,
  getProjectTemplates,
  type ProjectTemplateInfo,
} from "../api";
import { LoadingStatusRow } from "./LoadingStatusRow";
import { EliaButton, EliaModalActions, EliaModalOverlay, EliaModalPanel } from "./ui";

type Props = {
  c: Record<string, string>;
  open: boolean;
  onClose: () => void;
  /** Filtra plantillas recomendadas para web | api | any */
  contextPlatform?: "web" | "mobile" | "legacy" | "api" | "any";
  onCreated: (result: {
    projects: { platform: string; project: string }[];
    checklist: string[];
    message: string;
  }) => void;
};

function matchesContext(t: ProjectTemplateInfo, contextPlatform: Props["contextPlatform"]): boolean {
  if (!contextPlatform || contextPlatform === "any") return true;
  if (t.kind === "multi") return true;
  return t.platform === contextPlatform || (contextPlatform === "web" && t.platform === "web");
}

export function ProjectTemplateModal(props: Props) {
  const { c, open, onClose, contextPlatform = "any", onCreated } = props;
  const [templates, setTemplates] = React.useState<ProjectTemplateInfo[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedId, setSelectedId] = React.useState("");
  const [projectName, setProjectName] = React.useState("");
  const [doneChecklist, setDoneChecklist] = React.useState<string[] | null>(null);
  const [doneMessage, setDoneMessage] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open) return;
    setError(null);
    setDoneChecklist(null);
    setDoneMessage(null);
    setLoading(true);
    void getProjectTemplates()
      .then((r) => {
        const list = r.templates.filter((t) => matchesContext(t, contextPlatform));
        setTemplates(list);
        if (list.length > 0) {
          setSelectedId(list[0].id);
          setProjectName(list[0].default_project_name);
        }
      })
      .catch((e: unknown) => setError(String((e as Error)?.message ?? e)))
      .finally(() => setLoading(false));
  }, [open, contextPlatform]);

  React.useEffect(() => {
    const t = templates.find((x) => x.id === selectedId);
    if (t && !projectName.trim()) {
      setProjectName(t.default_project_name);
    }
  }, [selectedId, templates, projectName]);

  if (!open) return null;

  const selected = templates.find((t) => t.id === selectedId);

  const handleCreate = () => {
    if (!selectedId || !projectName.trim()) return;
    setBusy(true);
    setError(null);
    void createProjectFromTemplate(selectedId, projectName.trim())
      .then((r) => {
        setDoneChecklist(r.checklist);
        setDoneMessage(r.message);
        onCreated({
          projects: r.projects,
          checklist: r.checklist,
          message: r.message,
        });
      })
      .catch((e: unknown) => setError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  return (
    <EliaModalOverlay testId="elia-project-template-modal" ariaLabel="Nuevo proyecto desde plantilla" onClose={onClose}>
      <EliaModalPanel
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "min(640px, 96vw)",
          maxHeight: "min(88vh, 720px)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div style={{ padding: "18px 20px", borderBottom: `1px solid ${c.border}` }}>
          <div style={{ fontWeight: 800, fontSize: 17, color: c.text }}>Nuevo proyecto desde plantilla</div>
          <div style={{ fontSize: 13, color: c.muted, marginTop: 6, lineHeight: 1.5 }}>
            Empieza con escenarios listos para ejecutar en minutos. No sustituye tus proyectos existentes.
          </div>
        </div>

        <div style={{ flex: 1, overflow: "auto", padding: "16px 20px" }}>
          {loading ? (
            <LoadingStatusRow c={c} text="Cargando plantillas…" loading testId="elia-templates-loading" />
          ) : doneChecklist ? (
            <>
              <LoadingStatusRow
                c={c}
                text={doneMessage ?? "Proyecto creado."}
                tone="success"
                testId="elia-templates-done"
              />
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: c.text }}>Próximos pasos</div>
              <ol style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: c.text, lineHeight: 1.55 }}>
                {doneChecklist.map((item) => (
                  <li key={item} style={{ marginBottom: 6 }}>
                    {item}
                  </li>
                ))}
              </ol>
            </>
          ) : templates.length === 0 ? (
            <div style={{ fontSize: 13, color: c.muted }}>No hay plantillas disponibles.</div>
          ) : (
            <>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
                {templates.map((t) => {
                  const active = t.id === selectedId;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      data-testid={`elia-template-card-${t.id}`}
                      className={`elia-select-card${active ? " is-active" : ""}`}
                      onClick={() => {
                        setSelectedId(t.id);
                        setProjectName(t.default_project_name);
                      }}
                      style={{ textAlign: "left", color: c.text }}
                    >
                      <div style={{ fontWeight: 700, fontSize: 14 }}>{t.name}</div>
                      <div style={{ fontSize: 12, color: c.muted, marginTop: 4, lineHeight: 1.45 }}>{t.description}</div>
                      <div style={{ fontSize: 11, color: c.muted, marginTop: 6 }}>
                        ~{t.estimated_minutes} min
                        {t.kind === "multi" ? " · Web + API" : t.platform ? ` · ${t.platform}` : ""}
                      </div>
                    </button>
                  );
                })}
              </div>

              {selected?.prerequisites?.length ? (
                <div style={{ fontSize: 12, color: c.muted, marginBottom: 12 }}>
                  Requisitos: {selected.prerequisites.join(" · ")}
                </div>
              ) : null}

              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: c.text, marginBottom: 6 }}>
                Nombre del proyecto
              </label>
              <input
                data-testid="elia-template-project-name"
                className="elia-input"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder={selected?.default_project_name ?? "MiProyecto"}
                style={{ width: "100%", marginBottom: 8 }}
              />
              {selected?.kind === "multi" ? (
                <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>
                  Se crearán proyectos con sufijos -Web y -API (ej. {projectName.trim() || "ELIA-Demo"}-Web).
                </div>
              ) : null}
            </>
          )}

          {error ? (
            <div role="alert" style={{ marginTop: 12, fontSize: 13, color: c.errorTitle ?? "#c0392b" }}>
              {error}
            </div>
          ) : null}
        </div>

        <div style={{ padding: "14px 20px", borderTop: `1px solid ${c.border}` }}>
          <EliaModalActions>
            <EliaButton variant="ghost" size="sm" onClick={onClose}>
              {doneChecklist ? "Cerrar" : "Cancelar"}
            </EliaButton>
            {!doneChecklist && templates.length > 0 ? (
              <EliaButton
                variant="primary"
                size="sm"
                data-testid="elia-template-create-btn"
                disabled={busy || !projectName.trim() || !selectedId}
                onClick={handleCreate}
              >
                {busy ? "Creando…" : "Crear proyecto"}
              </EliaButton>
            ) : null}
          </EliaModalActions>
        </div>
      </EliaModalPanel>
    </EliaModalOverlay>
  );
}
