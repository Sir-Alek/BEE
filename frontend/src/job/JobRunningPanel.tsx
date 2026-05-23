import React from "react";
import { stopRecording } from "../api";
import { JobEventTimeline } from "./JobEventTimeline";
import type { JobEvent } from "./jobEvents";
import type { JobProgressState } from "./useJobProgress";

type Props = {
  c: Record<string, string>;
  jobId: string;
  job: JobProgressState;
  jobEvents: JobEvent[];
  stoppingRecording: boolean;
  setStoppingRecording: (v: boolean) => void;
  setErrorText: (v: string | null) => void;
};

export function JobRunningPanel(props: Props) {
  const { c, jobId, job, jobEvents, stoppingRecording, setStoppingRecording, setErrorText } = props;
  return (
    <>
      <div
        style={{
          background: c.processingBg,
          border: `1px solid ${c.processingBorder}`,
          color: c.processingText,
          padding: 12,
          borderRadius: 10,
          marginBottom: 16,
          fontSize: 14,
        }}
      >
        <div>
          {job.progress?.stage
            ? String(job.progress.stage)
            : "Procesando… (espera; esta pestaña no se cerrará sola)."}
        </div>
        {job.progress?.events_captured != null && (
          <div style={{ marginTop: 8, fontSize: 13 }}>
            Pantallas / eventos capturados: <b>{String(job.progress.events_captured)}</b>
            {job.progress?.elapsed_s != null ? ` · ${String(job.progress.elapsed_s)}s` : ""}
          </div>
        )}
        {Boolean(job.progress?.recording) && (
          <div style={{ marginTop: 12 }}>
            <button
              type="button"
              disabled={stoppingRecording}
              onClick={() => {
                setStoppingRecording(true);
                void stopRecording(jobId)
                  .catch((e: unknown) => {
                    setErrorText(String((e as Error)?.message ?? e));
                  })
                  .finally(() => setStoppingRecording(false));
              }}
              style={{
                padding: "10px 16px",
                borderRadius: 10,
                background: c.primary,
                color: c.primaryFg,
                border: "none",
                cursor: stoppingRecording ? "wait" : "pointer",
                fontWeight: 600,
              }}
            >
              {stoppingRecording ? "Finalizando…" : "Finalizar grabación"}
            </button>
          </div>
        )}
        <JobEventTimeline events={jobEvents} c={c} recordingOnly={Boolean(job.progress?.recording)} />
      </div>
      {String(job.progress?.stage ?? "").includes("Ejecutando Puppeteer") && (
        <div
          style={{
            background: c.warnBg,
            border: `1px solid ${c.warnBorder}`,
            color: c.warnText,
            padding: 12,
            borderRadius: 10,
            marginBottom: 16,
            fontSize: 14,
          }}
        >
          Se está abriendo el <b>navegador de grabación</b>. En Windows intentamos pasarlo al primer plano; si sigues
          viendo solo ELIA, revisa la barra de tareas u otras ventanas de Chrome/Chromium.
        </div>
      )}
    </>
  );
}
