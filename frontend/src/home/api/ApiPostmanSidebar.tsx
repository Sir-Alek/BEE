import React, { useEffect, useMemo, useRef, useState } from "react";
import { apiBtn, apiInputStyle } from "./apiUi";

export type ApiCollectionRow = { id: string; name: string; scenario_count: number };
export type ApiScenarioRow = { id: string; name: string; collection_id: string; collection_name?: string };

type Props = {
  c: Record<string, string>;
  busy: boolean;
  canRunJobs: boolean;
  scenariosLoading?: boolean;
  collections: ApiCollectionRow[];
  scenarios: ApiScenarioRow[];
  activeScenarioId: string | null;
  activeCollectionId: string;
  onActiveCollectionChange: (collectionId: string) => void;
  importKind: "postman" | "openapi";
  onImportKindChange: (kind: "postman" | "openapi") => void;
  onImportFile: (file: File) => void;
  captures: { id: string; name: string; path: string }[];
  onImportCapture: (captureId: string) => void;
  onLoadScenario: (scenarioId: string) => void;
  onRenameScenario: (scenarioId: string, newName: string) => void;
  onDeleteScenario: (scenarioId: string) => void;
  onDeleteCollection: (collectionId: string) => void;
  onCloneScenario?: (scenarioId: string) => void;
  webOriginAvailable?: boolean;
  onSyncFromWeb?: () => void;
};

export function ApiPostmanSidebar(props: Props) {
  const {
    c,
    busy,
    canRunJobs,
    scenariosLoading = false,
    collections,
    scenarios,
    activeScenarioId,
    activeCollectionId,
    onActiveCollectionChange,
    importKind,
    onImportKindChange,
    onImportFile,
    onImportCapture,
    captures,
    onLoadScenario,
    onRenameScenario,
    onDeleteScenario,
    onDeleteCollection,
    onCloneScenario,
    webOriginAvailable,
    onSyncFromWeb,
  } = props;
  const importRef = useRef<HTMLInputElement>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  const grouped = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const map = new Map<string, ApiScenarioRow[]>();
    for (const col of collections) {
      map.set(col.id, []);
    }
    for (const s of scenarios) {
      if (q && !s.name.toLowerCase().includes(q) && !s.id.toLowerCase().includes(q)) {
        continue;
      }
      const list = map.get(s.collection_id) ?? [];
      list.push(s);
      map.set(s.collection_id, list);
    }
    return collections
      .map((col) => ({ collection: col, scenarios: map.get(col.id) ?? [] }))
      .filter(({ scenarios: colScenarios }) => !q || colScenarios.length > 0);
  }, [collections, scenarios, searchQuery]);

  const commitRename = () => {
    if (!editingId) return;
    const trimmed = editingName.trim();
    const current = scenarios.find((s) => s.id === editingId);
    setEditingId(null);
    if (!trimmed || !current || trimmed === current.name) return;
    onRenameScenario(editingId, trimmed);
  };

  const toggleCollapsed = (collectionId: string) => {
    setCollapsed((prev) => ({ ...prev, [collectionId]: !prev[collectionId] }));
  };

  return (
    <div
      data-testid="elia-api-postman-sidebar"
      style={{
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        background: c.surface,
        padding: 12,
        minHeight: "min(62vh, 640px)",
        maxHeight: "min(72vh, 720px)",
        overflow: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <div>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Importar colección</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <select
            value={importKind}
            onChange={(e) => onImportKindChange(e.target.value as "postman" | "openapi")}
            style={apiInputStyle(c)}
          >
            <option value="postman">Colección v2.1 (JSON)</option>
            <option value="openapi">OpenAPI 3</option>
          </select>
          <input
            ref={importRef}
            type="file"
            accept=".json"
            style={{ display: "none" }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onImportFile(file);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            disabled={!canRunJobs || busy}
            onClick={() => importRef.current?.click()}
            style={apiBtn(c)}
          >
            Importar JSON
          </button>
        </div>
      </div>

      <div>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Capturas web</div>
        <div style={{ fontSize: 11, color: c.muted, marginBottom: 8, lineHeight: 1.4 }}>
          JSON en <code style={{ fontSize: 10 }}>behave/api/&lt;proyecto&gt;/scripts/</code>
          {webOriginAvailable && onSyncFromWeb ? (
            <div
              style={{
                marginTop: 8,
                padding: "8px 10px",
                borderRadius: 8,
                border: `1px solid ${c.primary}`,
                background: c.neutralBg,
              }}
            >
              <div style={{ fontWeight: 600, color: c.text, marginBottom: 4 }}>Puente web → API</div>
              <div style={{ marginBottom: 6 }}>
                Hay captura web en el proyecto. Importa tráfico abajo o sincroniza <code>base_url</code> desde la pestaña
                Cliente API.
              </div>
              <button type="button" disabled={busy} onClick={onSyncFromWeb} style={apiBtn(c, c.primary, c.primaryFg)}>
                Sincronizar base_url desde web
              </button>
            </div>
          ) : null}
        </div>
        {captures.length === 0 ? (
          <div style={{ fontSize: 12, color: c.muted }}>Sin capturas en este proyecto.</div>
        ) : (
          <ul style={{ margin: 0, padding: 0, listStyle: "none", fontSize: 12 }}>
            {captures.map((cap) => (
              <li
                key={cap.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  marginBottom: 10,
                  paddingBottom: 10,
                  borderBottom: `1px solid ${c.border}`,
                }}
              >
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={cap.path}>
                  {cap.name}
                </span>
                <button
                  type="button"
                  disabled={!canRunJobs || busy}
                  onClick={() => onImportCapture(cap.id)}
                  style={apiBtn(c, undefined, undefined, true)}
                >
                  Importar a escenarios
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ flex: "1 1 auto", minHeight: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>
          Colecciones ({collections.length}) · {scenarios.length} escenario(s)
        </div>
        <div style={{ fontSize: 11, color: c.muted, marginBottom: 8 }}>
          Doble clic en un escenario para renombrar. Nuevos escenarios se guardan en la colección activa.
        </div>
        <div style={{ marginBottom: 10 }}>
          <label style={{ fontSize: 11, color: c.muted, display: "block", marginBottom: 4 }}>Colección activa (guardar)</label>
          <select
            value={activeCollectionId}
            onChange={(e) => onActiveCollectionChange(e.target.value)}
            style={apiInputStyle(c, { width: "100%" })}
          >
            {collections.map((col) => (
              <option key={col.id} value={col.id}>
                {col.name} ({col.scenario_count})
              </option>
            ))}
          </select>
        </div>
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filtrar escenarios…"
          style={apiInputStyle(c, { width: "100%", marginBottom: 10 })}
          data-testid="elia-api-scenario-search"
        />
        {scenariosLoading ? (
          <div
            data-testid="elia-api-scenarios-loading"
            style={{ fontSize: 12, color: c.muted, display: "flex", alignItems: "center", gap: 8 }}
          >
            <span
              aria-hidden
              style={{
                width: 14,
                height: 14,
                borderRadius: "50%",
                border: `2px solid ${c.border}`,
                borderTopColor: c.primary,
                animation: "elia-spin 0.8s linear infinite",
              }}
            />
            Cargando colecciones…
          </div>
        ) : grouped.length === 0 ? (
          <div style={{ fontSize: 12, color: c.muted }}>Sin colecciones. Importa JSON o guarda un escenario.</div>
        ) : (
          grouped.map(({ collection, scenarios: colScenarios }) => {
            const isCollapsed = collapsed[collection.id] ?? false;
            const isDefault = collection.id === "_default";
            const deleteTitle = isDefault
              ? "Vaciar colección General (eliminar todos los escenarios)"
              : "Eliminar colección completa";
            return (
              <div
                key={collection.id}
                style={{
                  marginBottom: 10,
                  border: `1px solid ${c.border}`,
                  borderRadius: 8,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "8px 10px",
                    background: collection.id === activeCollectionId ? c.neutralBg : c.surface,
                    borderBottom: isCollapsed ? undefined : `1px solid ${c.border}`,
                  }}
                >
                  <button
                    type="button"
                    onClick={() => toggleCollapsed(collection.id)}
                    style={apiBtn(c, undefined, undefined, true)}
                    title={isCollapsed ? "Expandir" : "Contraer"}
                  >
                    {isCollapsed ? "▸" : "▾"}
                  </button>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {collection.name}
                    </div>
                    <div style={{ fontSize: 10, color: c.muted }}>{colScenarios.length} escenario(s)</div>
                  </div>
                  <button
                    type="button"
                    disabled={busy || colScenarios.length === 0}
                    title={deleteTitle}
                    onClick={() => onDeleteCollection(collection.id)}
                    style={{
                      ...apiBtn(c, undefined, undefined, true),
                      padding: "4px 7px",
                      fontSize: 11,
                      lineHeight: 1,
                      minWidth: 24,
                      flexShrink: 0,
                    }}
                  >
                    ✕
                  </button>
                </div>
                {!isCollapsed ? (
                  <ul style={{ margin: 0, padding: "6px 8px 8px", listStyle: "none", fontSize: 12 }}>
                    {colScenarios.length === 0 ? (
                      <li style={{ color: c.muted, padding: "4px 2px" }}>Sin escenarios.</li>
                    ) : (
                      colScenarios.map((s) => {
                        const active = activeScenarioId === s.id;
                        const editing = editingId === s.id;
                        return (
                          <li key={s.id} style={{ marginBottom: 4 }}>
                            {editing ? (
                              <input
                                ref={editInputRef}
                                value={editingName}
                                onChange={(e) => setEditingName(e.target.value)}
                                onBlur={commitRename}
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") commitRename();
                                  if (e.key === "Escape") setEditingId(null);
                                }}
                                style={apiInputStyle(c, { width: "100%" })}
                              />
                            ) : (
                              <div style={{ display: "flex", gap: 4, alignItems: "stretch" }}>
                                <button
                                  type="button"
                                  disabled={busy}
                                  title={`${s.name}\n${s.id}`}
                                  onClick={() => onLoadScenario(s.id)}
                                  onDoubleClick={(e) => {
                                    e.preventDefault();
                                    setEditingId(s.id);
                                    setEditingName(s.name);
                                  }}
                                  style={{
                                    ...apiBtn(c, active ? c.primary : undefined, active ? c.primaryFg : undefined, !active),
                                    flex: 1,
                                    textAlign: "left",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                    border: active ? `2px solid ${c.primary}` : undefined,
                                    fontWeight: active ? 700 : 600,
                                  }}
                                >
                                  {s.name}
                                </button>
                                {onCloneScenario ? (
                                  <button
                                    type="button"
                                    disabled={busy}
                                    title="Duplicar escenario"
                                    onClick={() => onCloneScenario(s.id)}
                                    style={apiBtn(c, undefined, undefined, true)}
                                  >
                                    ✎
                                  </button>
                                ) : null}
                                <button
                                  type="button"
                                  disabled={busy}
                                  title="Eliminar escenario"
                                  onClick={() => onDeleteScenario(s.id)}
                                  style={apiBtn(c, undefined, undefined, true)}
                                >
                                  ✕
                                </button>
                              </div>
                            )}
                          </li>
                        );
                      })
                    )}
                  </ul>
                ) : null}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
