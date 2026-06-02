import { useCallback, useEffect, useRef, useState } from "react";
import { getJob, getJobEvents, type JobStateResponse } from "../api";
import { closeWithoutStoppingServer } from "../app/sessionGuard";
import type { ActivePrompt } from "../types";
import type { JobEvent } from "./jobEvents";

export type JobProgressState = {
  job_id: string;
  state: string;
  active_prompt: ActivePrompt | null;
  error: null | { message: string; details?: string };
  progress: Record<string, unknown>;
};

const POLL_IDLE_MS = 450;
const POLL_RECORDING_MS = 120;

function mapJobResponse(j: JobStateResponse): JobProgressState {
  return {
    job_id: j.job_id,
    state: j.state,
    active_prompt: j.active_prompt as ActivePrompt | null,
    error: j.error,
    progress: j.progress ?? {},
  };
}

export function useJobProgress(jobId: string | null, polling: boolean) {
  const [job, setJob] = useState<JobProgressState | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [errorText, setErrorText] = useState<string | null>(null);
  const sinceIndexRef = useRef(0);
  const recordingRef = useRef(false);

  const reset = useCallback(() => {
    sinceIndexRef.current = 0;
    recordingRef.current = false;
    setEvents([]);
  }, []);

  useEffect(() => {
    if (!jobId) {
      reset();
      setJob(null);
    }
  }, [jobId, reset]);

  useEffect(() => {
    if (!polling || !jobId) return;

    let alive = true;
    let timer: number | null = null;

    const schedule = (delayMs: number) => {
      if (timer != null) window.clearTimeout(timer);
      timer = window.setTimeout(() => void tick(), delayMs);
    };

    const tick = async () => {
      if (!alive) return;
      try {
        const j = await getJob(jobId);
        if (!alive) return;

        const mapped = mapJobResponse(j);
        setJob(mapped);
        recordingRef.current = Boolean(mapped.progress?.recording);

        const evRes = await getJobEvents(jobId, sinceIndexRef.current);
        if (!alive) return;
        if (evRes.events.length > 0) {
          setEvents((prev) => [...prev, ...evRes.events]);
          sinceIndexRef.current = evRes.next_index;
        }

        if (j.state === "done" || j.state === "error" || j.state === "cancelled") {
          return;
        }

        schedule(recordingRef.current ? POLL_RECORDING_MS : POLL_IDLE_MS);
      } catch (e: unknown) {
        if (!alive) return;
        const msg = String((e as Error)?.message ?? e);
        if (/404|not found|job not found/i.test(msg)) {
          setJob(null);
          setErrorText(null);
          closeWithoutStoppingServer();
          return;
        }
        setErrorText(msg);
      }
    };

    void tick();

    return () => {
      alive = false;
      if (timer != null) window.clearTimeout(timer);
    };
  }, [polling, jobId]);

  return { job, events, errorText, setErrorText, resetEvents: reset };
}

export function jobPollingActive(state: string | undefined): boolean {
  return state !== "done" && state !== "error" && state !== "cancelled";
}
