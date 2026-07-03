import { useEffect, useMemo, useRef, useState } from "react";

export type BootPhase = 1 | 2 | 3 | 4;

export type EliaBootSnapshot = {
  phase: BootPhase;
  title: string;
  subtitle: string;
  pillarsActive: [boolean, boolean, boolean, boolean];
  progressStep: number;
  scannerPulse: number;
  bootComplete: boolean;
};

type Options = {
  enabled: boolean;
  licenseLoading: boolean;
  modulesLoading: boolean;
  modulesReady: boolean;
  canRunJobs: boolean;
  licenseBlocked: boolean;
  reducedMotion?: boolean;
};

const PHASE_STEP_MS = 420;

const PHASE_COPY: Record<
  BootPhase,
  { title: string; subtitle: string; pillars: [boolean, boolean, boolean, boolean] }
> = {
  1: {
    title: "INICIANDO NÚCLEO ELIA",
    subtitle: "Inicializando entorno de arranque…",
    pillars: [false, false, false, false],
  },
  2: {
    title: "AUTENTICACIÓN",
    subtitle: "Verificando licencia…",
    pillars: [true, false, false, false],
  },
  3: {
    title: "SINCRONIZANDO MÓDULOS",
    subtitle: "Cargando capacidades del sistema…",
    pillars: [true, true, true, false],
  },
  4: {
    title: "SISTEMA LISTO",
    subtitle: "Entorno operativo",
    pillars: [true, true, true, true],
  },
};

function targetPhase(opts: Options): BootPhase {
  if (!opts.enabled) return 4;
  if (opts.licenseLoading) return 1;
  if (opts.canRunJobs && !opts.modulesReady) return 3;
  if (!opts.licenseLoading && opts.modulesReady) return 4;
  if (!opts.licenseLoading) return 2;
  return 1;
}

function snapshotForPhase(
  phase: BootPhase,
  licenseBlocked: boolean,
  modulesLoading: boolean,
): EliaBootSnapshot {
  const base = PHASE_COPY[phase];
  let subtitle = base.subtitle;
  let title = base.title;

  if (phase === 2 && !licenseBlocked) {
    subtitle = "Licencia validada";
  }
  if (phase === 2 && licenseBlocked) {
    title = "ACCESO DENEGADO";
    subtitle = "Licencia no activa o expirada";
  }
  if (phase === 3 && modulesLoading) {
    subtitle = "Cargando capacidades del sistema…";
  } else if (phase === 3) {
    subtitle = "Módulos en línea";
  }
  if (phase === 4 && licenseBlocked) {
    subtitle = "Redirigiendo…";
  }

  return {
    phase,
    title,
    subtitle,
    pillarsActive: base.pillars,
    progressStep: phase,
    scannerPulse: phase,
    bootComplete: phase >= 4,
  };
}

/** Secuencia narrativa de arranque ELIA (licencia → módulos → listo). */
export function useEliaBootSequence(opts: Options): EliaBootSnapshot {
  const target = targetPhase(opts);
  const displayRef = useRef<BootPhase>(1);
  const [displayPhase, setDisplayPhase] = useState<BootPhase>(1);
  const reducedMotion = opts.reducedMotion ?? false;

  useEffect(() => {
    if (!opts.enabled) {
      return;
    }

    if (reducedMotion) {
      displayRef.current = target;
      setDisplayPhase(target);
      return;
    }

    const current = displayRef.current;
    if (current > target) {
      displayRef.current = target;
      setDisplayPhase(target);
      return;
    }
    if (current >= target) return;

    if (target - current === 1) {
      displayRef.current = target;
      setDisplayPhase(target);
      return;
    }

    let step = current;
    const id = window.setInterval(() => {
      step = Math.min(4, step + 1) as BootPhase;
      displayRef.current = step;
      setDisplayPhase(step);
      if (step >= target) window.clearInterval(id);
    }, PHASE_STEP_MS);

    return () => window.clearInterval(id);
  }, [target, opts.enabled, reducedMotion]);

  useEffect(() => {
    if (opts.enabled) return;
    displayRef.current = 4;
    setDisplayPhase(4);
  }, [opts.enabled]);

  return useMemo(
    () => snapshotForPhase(displayPhase, opts.licenseBlocked, opts.modulesLoading),
    [displayPhase, opts.licenseBlocked, opts.modulesLoading],
  );
}
