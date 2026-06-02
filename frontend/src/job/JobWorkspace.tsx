import React, { useEffect } from "react";
import { JobErrorActions, JobErrorPanel } from "./JobErrorPanel";
import { JobPromptRouter } from "./JobPromptRouter";
import { JobRunningPanel } from "./JobRunningPanel";
import { JobCancelledPanel, JobDonePanel } from "./JobTerminalPanels";
import { cancelConvertJob } from "../api";
import { isReloadNavigation, requestAppExitIfClosingWhenOrphanJobTab } from "../app/homeNavigation";
import { broadcastJobTabClosed } from "./promptNav";import type { JobEvent } from "./jobEvents";
import type { JobProgressState } from "./useJobProgress";
import type { ActivePrompt } from "../types";

export type JobWorkspaceProps = {
  c: Record<string, string>;
  jobId: string | null;
  job: JobProgressState | null;
  jobEvents: JobEvent[];
  activePrompt: ActivePrompt | null;
  stoppingRecording: boolean;
  setStoppingRecording: (v: boolean) => void;
  setErrorText: (v: string | null) => void;
  textValue: string;
  setTextValue: (v: string) => void;
  bddPreviewText: string;
  setBddPreviewText: (v: string) => void;
  betaFeedbackUrl?: string | null;
  jobLoadError?: string | null;
  /** Versión comercial: aboutInfo?.support_email (ver JobErrorPanel.tsx) */
  // supportEmail?: string | null;
};

export function JobWorkspace(props: JobWorkspaceProps) {
  const {
    c, jobId, job, jobEvents, activePrompt, stoppingRecording, setStoppingRecording,
    setErrorText, textValue, setTextValue, bddPreviewText, setBddPreviewText, betaFeedbackUrl, jobLoadError,
  } = props;

  useEffect(() => {
    if (!jobId) return;
    const onPageHide = () => {
      if (isReloadNavigation()) return;
      requestAppExitIfClosingWhenOrphanJobTab();
      if (sessionStorage.getItem(`elia_job_finished_broadcast:${jobId}`)) return;
      broadcastJobTabClosed(jobId);
      void cancelConvertJob(jobId).catch(() => {});
    };
    window.addEventListener("pagehide", onPageHide);
    return () => window.removeEventListener("pagehide", onPageHide);
  }, [jobId]);

  return (
    <>
      {!job && jobId && !jobLoadError && <div style={{ color: c.muted }}>Cargando...</div>}
      {!job && jobId && jobLoadError ? (
        <div style={{ color: c.errorBody ?? c.muted, fontSize: 14 }}>
          {jobLoadError} Esta pestaña se cerrará sola…
        </div>
      ) : null}

      {job && job.state === "running" && !activePrompt && jobId && (
        <JobRunningPanel
          c={c}
          jobId={jobId}
          job={job}
          jobEvents={jobEvents}
          stoppingRecording={stoppingRecording}
          setStoppingRecording={setStoppingRecording}
          setErrorText={setErrorText}
        />
      )}

      {job?.error && jobId && (
        <JobErrorPanel
          c={c}
          jobId={jobId}
          errorMessage={job.error.message}
          betaFeedbackUrl={betaFeedbackUrl}
          onDownloadError={setErrorText}
        />
      )}

      {job?.state === "waiting_user" && activePrompt && jobId && (
        <JobPromptRouter
          c={c}
          jobId={jobId}
          job={job}
          activePrompt={activePrompt}
          textValue={textValue}
          setTextValue={setTextValue}
          bddPreviewText={bddPreviewText}
          setBddPreviewText={setBddPreviewText}
        />
      )}

      {job?.state === "done" && <JobDonePanel c={c} job={job} />}

      {job?.state === "error" && !job.error && <JobErrorActions c={c} />}

      {job?.state === "cancelled" && <JobCancelledPanel c={c} />}
    </>
  );
}
