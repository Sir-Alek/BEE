import React, { useMemo, useState } from "react";
import type { ApiCollectionRow, ApiScenarioRow } from "./ApiPostmanSidebar";
import { EliaButton } from "../../components/ui";
import { apiInputStyle } from "./apiUi";

type Props = {
  c: Record<string, string>;
  busy: boolean;
  scenarios: ApiScenarioRow[];
  collections: ApiCollectionRow[];
  selectedScenarios: Record<string, boolean>;
  scenarioWeights: Record<string, string>;
  locustAccess: boolean;
  onSelectedChange: (next: Record<string, boolean>) => void;
  onWeightChange: (scenarioId: string, value: string) => void;
  onLoadScenario: (scenarioId: string) => void;
  onDeleteSelected: (scenarioIds: string[]) => void;
};

export function ApiSuiteScenarioPicker(props: Props) {
  const {
    c,
    busy,
    scenarios,
    collections,
    selectedScenarios,
    scenarioWeights,
    locustAccess,
    onSelectedChange,
    onWeightChange,
    onLoadScenario,
    onDeleteSelected,
  } = props;
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const grouped = useMemo(() => {
    const map = new Map<string, ApiScenarioRow[]>();
    for (const col of collections) map.set(col.id, []);
    for (const s of scenarios) {
      const list = map.get(s.collection_id) ?? [];
      list.push(s);
      map.set(s.collection_id, list);
    }
    return collections
      .map((col) => ({ collection: col, items: map.get(col.id) ?? [] }))
      .filter(({ items }) => items.length > 0);
  }, [collections, scenarios]);

  const selectedIds = scenarios.filter((s) => selectedScenarios[s.id]).map((s) => s.id);
  const allSelected = scenarios.length > 0 && scenarios.every((s) => selectedScenarios[s.id]);

  const setAll = (checked: boolean) => {
    const next: Record<string, boolean> = {};
    for (const s of scenarios) next[s.id] = checked;
    onSelectedChange(next);
  };

  const setCollection = (collectionId: string, checked: boolean) => {
    const next = { ...selectedScenarios };
    for (const s of scenarios) {
      if (s.collection_id === collectionId) next[s.id] = checked;
    }
    onSelectedChange(next);
  };

  if (!scenarios.length) {
    return <div style={{ fontSize: 13, color: c.muted }}>Sin escenarios guardados.</div>;
  }

  return (
    <>
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 10, lineHeight: 1.45 }}>
        Selecciona escenarios para suite o carga. Edita URLs, headers y scripts en la pestaña{" "}
        <strong>Cliente API</strong>.
      </div>
      <div
        style={{
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          alignItems: "center",
          marginBottom: 10,
          position: "sticky",
          top: 0,
          background: c.surface,
          paddingBottom: 6,
          zIndex: 1,
        }}
      >
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
          <input type="checkbox" checked={allSelected} onChange={(e) => setAll(e.target.checked)} />
          Seleccionar todos
        </label>
        {selectedIds.length ? (
          <EliaButton variant="ghost" size="sm" disabled={busy} onClick={() => onDeleteSelected(selectedIds)}>
            Eliminar seleccionados ({selectedIds.length})
          </EliaButton>
        ) : null}
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        {grouped.map(({ collection, items }) => {
          const colSelected = items.every((s) => selectedScenarios[s.id]);
          const colPartial = !colSelected && items.some((s) => selectedScenarios[s.id]);
          const isCollapsed = collapsed[collection.id] ?? false;
          return (
            <div
              key={collection.id}
              style={{
                border: `1px solid ${c.border}`,
                borderRadius: 10,
                overflow: "hidden",
                background: c.neutralBg,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 10px",
                  background: c.surface,
                  borderBottom: isCollapsed ? "none" : `1px solid ${c.border}`,
                }}
              >
                <button
                  type="button"
                  onClick={() => setCollapsed((prev) => ({ ...prev, [collection.id]: !isCollapsed }))}
                  style={{
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                    color: c.muted,
                    fontSize: 12,
                    padding: 0,
                  }}
                  aria-expanded={!isCollapsed}
                >
                  {isCollapsed ? "▸" : "▾"}
                </button>
                <label style={{ display: "flex", alignItems: "center", gap: 6, flex: 1, fontSize: 13, fontWeight: 700 }}>
                  <input
                    type="checkbox"
                    checked={colSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = colPartial;
                    }}
                    onChange={(e) => setCollection(collection.id, e.target.checked)}
                  />
                  {collection.name}
                  <span style={{ fontWeight: 500, color: c.muted, fontSize: 12 }}>
                    ({items.filter((s) => selectedScenarios[s.id]).length}/{items.length})
                  </span>
                </label>
              </div>
              {!isCollapsed ? (
                <ul style={{ margin: 0, padding: "8px 10px 8px 28px", listStyle: "none", fontSize: 13 }}>
                  {items.map((s) => (
                    <li
                      key={s.id}
                      style={{
                        display: "flex",
                        gap: 8,
                        alignItems: "center",
                        marginBottom: 6,
                        flexWrap: "wrap",
                      }}
                    >
                      <label style={{ display: "flex", alignItems: "center", gap: 6, flex: 1, minWidth: 160 }}>
                        <input
                          type="checkbox"
                          checked={!!selectedScenarios[s.id]}
                          onChange={(e) =>
                            onSelectedChange({ ...selectedScenarios, [s.id]: e.target.checked })
                          }
                        />
                        {s.name}
                      </label>
                      {locustAccess ? (
                        <input
                          type="number"
                          min={1}
                          value={scenarioWeights[s.id] ?? "1"}
                          onChange={(e) => onWeightChange(s.id, e.target.value)}
                          title="Peso Locust"
                          style={{ ...apiInputStyle(c, { width: 56 }), padding: "4px 6px" }}
                        />
                      ) : null}
                      <EliaButton variant="ghost" size="sm" disabled={busy} onClick={() => onLoadScenario(s.id)}>
                        Abrir
                      </EliaButton>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          );
        })}
      </div>
    </>
  );
}
