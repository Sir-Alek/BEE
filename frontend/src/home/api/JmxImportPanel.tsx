import React, { useState } from "react";

import { importJmxPlan, previewJmxPlan, type JmxImportReport, type JmxImportResult } from "../../api";

import { ConfirmModal } from "../../components/ConfirmModal";
import { FileDropZone } from "../../components/FileDropZone";
import { EliaButton } from "../../components/ui";



type Theme = Record<string, string>;



type Props = {

  c: Theme;

  project: string;

  busy: boolean;

  onError: (msg: string) => void;

  onHint: (msg: string) => void;

  onImported?: (result: JmxImportResult) => void;

};



export function JmxImportPanel(props: Props) {

  const { c, project, busy, onError, onHint, onImported } = props;

  const [uploadBusy, setUploadBusy] = useState(false);

  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const [threadGroupIndex, setThreadGroupIndex] = useState(0);

  const [includeDisabledControllers, setIncludeDisabledControllers] = useState(false);

  const [report, setReport] = useState<JmxImportReport | null>(null);

  const [confirmOpen, setConfirmOpen] = useState(false);



  const runPreview = (file: File, tgIndex = threadGroupIndex, forceAll = includeDisabledControllers) => {

    if (!project.trim()) {

      onError("Selecciona un proyecto API.");

      return;

    }

    setUploadBusy(true);

    setPendingFile(file);

    void previewJmxPlan(project, file, tgIndex, forceAll)

      .then((r) => {

        setReport(r.report);

        setThreadGroupIndex(r.report.thread_group_index);

        setIncludeDisabledControllers(!!r.report.include_disabled_controllers);

      })

      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)))

      .finally(() => setUploadBusy(false));

  };



  const commitImport = () => {

    if (!pendingFile || !project.trim()) return;

    setUploadBusy(true);

    void importJmxPlan(project, pendingFile, threadGroupIndex, includeDisabledControllers)

      .then((r) => {

        setConfirmOpen(false);

        setReport(null);

        setPendingFile(null);

        onImported?.(r);

        onHint(`Plan .jmx importado: ${r.count} escenarios, flujo «${r.flow_name}».`);

      })

      .catch((e: unknown) => onError(String((e as Error)?.message ?? e)))

      .finally(() => setUploadBusy(false));

  };



  return (

    <div style={{ marginBottom: 16 }}>

      <div style={{ fontSize: 12, color: c.muted, marginBottom: 8, lineHeight: 1.45 }}>

        Asistente de migración acelerada: importa HTTP, headers, variables, CSV, extractores regex y traducción asistida

        de Groovy simple. Scripts complejos quedan como stub comentado para revisión en Cliente API.

      </div>

      <FileDropZone

        c={c}

        accept=".jmx"

        extensions={[".jmx"]}

        acceptLabel=".jmx"

        disabled={busy}

        busy={uploadBusy}

        onFiles={(files: File[]) => runPreview(files[0])}

        onInvalidFiles={onError}

        testId="elia-jmx-drop"

      />



      {report ? (

        <div

          style={{

            marginTop: 10,

            padding: 12,

            borderRadius: 10,

            border: `1px solid ${c.border}`,

            background: c.neutralBg,

            fontSize: 13,

          }}

        >

          <div style={{ fontWeight: 800, color: c.text, marginBottom: 8 }}>

            Migración parcial — {report.source_file}

          </div>

          {report.thread_groups.length > 1 ? (

            <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10, fontSize: 12 }}>

              <span style={{ color: c.muted }}>Thread Group</span>

              <select

                value={threadGroupIndex}

                onChange={(e) => {

                  const idx = Number(e.target.value);

                  setThreadGroupIndex(idx);

                  if (pendingFile) runPreview(pendingFile, idx);

                }}

                style={{

                  padding: "6px 8px",

                  borderRadius: 8,

                  border: `1px solid ${c.inputBorder}`,

                  background: c.inputBg,

                  color: c.text,

                }}

              >

                {report.thread_groups.map((tg) => (

                  <option key={tg.index} value={tg.index} disabled={!tg.enabled}>

                    {tg.name} ({tg.sampler_count} HTTP{tg.enabled ? "" : ", deshabilitado"})

                  </option>

                ))}

              </select>

            </label>

          ) : null}



          <label

            style={{

              display: "flex",

              alignItems: "flex-start",

              gap: 8,

              marginBottom: 10,

              fontSize: 12,

              color: c.text,

              cursor: "pointer",

            }}

          >

            <input

              type="checkbox"

              checked={includeDisabledControllers}

              onChange={(e) => {

                const checked = e.target.checked;

                setIncludeDisabledControllers(checked);

                if (pendingFile) runPreview(pendingFile, threadGroupIndex, checked);

              }}

              style={{ marginTop: 2 }}

            />

            <span>

              Incluir samplers bajo controladores deshabilitados (modo forzar todo). Por defecto ELIA respeta la lógica

              de JMeter.

            </span>

          </label>



          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 10, fontSize: 12 }}>

            <span style={{ color: c.successHint ?? c.primary }}>

              Estructura: {report.structural_coverage_pct}%

            </span>

            <span style={{ color: c.warnText ?? c.muted }}>Ejecutable estimado: {report.executability_pct}%</span>

          </div>



          <div style={{ color: c.text, marginBottom: 8 }}>

            ✅ {report.imported_http} peticiones HTTP · {report.imported_extractors} extractores ·{" "}

            {Object.keys(report.imported_variables).length} variables · {report.csv_refs.length} CSV referenciados

            {(report.groovy_translations?.length ?? 0) > 0

              ? ` · ${report.groovy_translations?.length} script(s) Groovy traducidos`

              : ""}

          </div>



          {report.scenario_names.length ? (

            <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>

              Escenarios: {report.scenario_names.slice(0, 8).join(", ")}

              {report.scenario_names.length > 8 ? "…" : ""}

            </div>

          ) : null}



          {report.warnings.length ? (

            <div

              style={{

                marginBottom: 8,

                padding: 8,

                borderRadius: 8,

                background: c.warnBg,

                border: `1px solid ${c.warnBorder}`,

                fontSize: 12,

                color: c.warnText,

              }}

            >

              <div style={{ fontWeight: 700, marginBottom: 4 }}>⚠️ Requiere revisión manual ({report.warnings.length})</div>

              <ul style={{ margin: 0, paddingLeft: 18 }}>

                {report.warnings.slice(0, 6).map((w, i) => (

                  <li key={i}>{w.message}</li>

                ))}

                {report.warnings.length > 6 ? <li>… y {report.warnings.length - 6} más</li> : null}

              </ul>

            </div>

          ) : null}



          {report.load_suggestion?.users != null ? (

            <div style={{ fontSize: 12, color: c.muted, marginBottom: 10 }}>

              Sugerencia Locust: {String(report.load_suggestion.users)} usuarios, rampa{" "}

              {String(report.load_suggestion.ramp_time_sec ?? "?")}s, duración{" "}

              {String(report.load_suggestion.run_time ?? "?")} (perfil{" "}

              {String(report.load_suggestion.profile ?? "load")}). Se aplicará al importar.

            </div>

          ) : null}



          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <EliaButton variant="primary" size="sm" disabled={busy || uploadBusy} onClick={() => setConfirmOpen(true)}>
              Importar estructura a ELIA
            </EliaButton>
            <EliaButton
              variant="ghost"
              size="sm"
              disabled={busy || uploadBusy}
              onClick={() => {
                setReport(null);
                setPendingFile(null);
              }}
            >
              Cancelar
            </EliaButton>
          </div>

        </div>

      ) : null}



      {confirmOpen && report ? (

        <ConfirmModal

          c={c}

          title="Importar plan .jmx"

          message={`Se creará la colección con ${report.imported_http} escenarios, un flujo suite encadenado y variables de entorno. Los scripts omitidos o en stub deberás revisarlos en Cliente API.`}

          confirmLabel="Importar"

          onCancel={() => setConfirmOpen(false)}

          onConfirm={commitImport}

        />

      ) : null}

    </div>

  );

}


