import React from "react";
import type { EliaBootSnapshot } from "../hooks/useEliaBootSequence";
import { SplashHudRings } from "./SplashHudRings";
import "./EliaSplashScreen.css";
import logoEliaFull from "../../../resources/logo_elia_full.png";

type Props = EliaBootSnapshot & {
  fading?: boolean;
};

const PILLAR_ICON_PROPS = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.35,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

const PILLARS = [
  {
    label: "SEGURIDAD",
    icon: (
      <svg {...PILLAR_ICON_PROPS}>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="m9 12 2 2 4-4" />
      </svg>
    ),
  },
  {
    label: "INTELIGENCIA",
    icon: (
      <svg {...PILLAR_ICON_PROPS}>
        <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
        <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
        <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
        <path d="M17.599 6.5A3 3 0 0 0 13.6 4.6" />
        <path d="M6.401 6.5A3 3 0 0 1 10.4 4.6" />
      </svg>
    ),
  },
  {
    label: "AUTOMATIZACIÓN",
    icon: (
      <svg {...PILLAR_ICON_PROPS}>
        <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
        <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
        <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" />
        <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" />
      </svg>
    ),
  },
  {
    label: "EVOLUCIÓN",
    icon: (
      <svg {...PILLAR_ICON_PROPS}>
        <line x1="12" y1="20" x2="12" y2="10" />
        <line x1="18" y1="20" x2="18" y2="4" />
        <line x1="6" y1="20" x2="6" y2="16" />
        <rect x="3" y="20" width="18" height="2" rx="1" />
      </svg>
    ),
  },
] as const;

export function EliaSplashScreen({
  phase,
  title,
  subtitle,
  pillarsActive,
  progressStep,
  scannerPulse,
  fading = false,
}: Props) {
  return (
    <div
      className={`elia-splash${fading ? " elia-splash--fade-out" : ""}`}
      data-phase={phase}
      role="status"
      aria-live="polite"
      aria-busy={!fading}
      data-testid="elia-splash"
    >
      <div className="elia-splash__backdrop" aria-hidden />
      <div className="elia-splash__dots-bg" aria-hidden />
      <div className="elia-splash__particles" aria-hidden>
        <span className="elia-splash__particle elia-splash__particle--tl" />
        <span className="elia-splash__particle elia-splash__particle--tr" />
        <span className="elia-splash__particle elia-splash__particle--bl" />
        <span className="elia-splash__particle elia-splash__particle--br" />
      </div>

      <div className="elia-splash__stage">
        <div className="elia-splash__hud">
          <SplashHudRings phase={phase} />
          <div key={scannerPulse} className="elia-splash__scanner elia-splash__scanner--pulse" />
          <div className="elia-splash__brand-stack">
            <div className="elia-splash__brand-glow" aria-hidden />
            <img src={logoEliaFull} alt="ELIA" className="elia-splash__logo-full" />
          </div>
        </div>

        <div className="elia-splash__loading-block">
          <div className="elia-splash__loading">{title}</div>
          <div className="elia-splash__progress" aria-hidden>
            {[1, 2, 3, 4].map((step) => (
              <span
                key={step}
                className={`elia-splash__progress-seg${progressStep >= step ? " is-active" : ""}`}
              />
            ))}
          </div>
          <div className="elia-splash__status">{subtitle}</div>
        </div>
      </div>

      <div className="elia-splash__pillars" aria-hidden>
        {PILLARS.map((p, i) => (
          <React.Fragment key={p.label}>
            {i > 0 ? <span className="elia-splash__pillar-sep">·</span> : null}
            <div className={`elia-splash__pillar${pillarsActive[i] ? " is-active" : ""}`}>
              <span className="elia-splash__pillar-icon">{p.icon}</span>
              <span className="elia-splash__pillar-label">{p.label}</span>
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
