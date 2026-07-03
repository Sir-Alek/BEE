import React from "react";

type Props = {
  phase: number;
};

export function SplashHudRings({ phase }: Props) {
  return (
    <svg className="elia-splash__hud-svg" viewBox="0 0 400 400" aria-hidden>
      <defs>
        <linearGradient id="eliaHudCyan" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#00d2ff" />
          <stop offset="100%" stopColor="#38bdf8" />
        </linearGradient>
        <linearGradient id="eliaHudMagenta" x1="100%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#ec4899" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
        <linearGradient id="eliaHudMix" x1="0%" y1="50%" x2="100%" y2="50%">
          <stop offset="0%" stopColor="#00d2ff" />
          <stop offset="50%" stopColor="#60a5fa" />
          <stop offset="100%" stopColor="#ec4899" />
        </linearGradient>
        <radialGradient id="eliaGlow">
          <stop offset="0%" stopColor="rgba(0,210,255,.18)" />
          <stop offset="70%" stopColor="rgba(0,210,255,.04)" />
          <stop offset="100%" stopColor="rgba(0,0,0,0)" />
        </radialGradient>
      </defs>

      <circle cx="200" cy="200" r="170" fill="url(#eliaGlow)" />

      <g className="elia-splash__svg-ring elia-splash__svg-ring--outer">
        <circle
          cx="200"
          cy="200"
          r="184"
          fill="none"
          stroke="url(#eliaHudMagenta)"
          strokeWidth="4"
          strokeDasharray="68 22 18 40 52 18"
          strokeLinecap="round"
        />
        <circle
          cx="200"
          cy="200"
          r="176"
          fill="none"
          stroke="rgba(255,255,255,.12)"
          strokeWidth="1"
          strokeDasharray="2 12"
        />
        <g className="elia-splash__flare">
          <path
            d="M 200 16 A 184 184 0 0 1 318 72"
            fill="none"
            stroke="#00d2ff"
            strokeWidth="5"
            strokeLinecap="round"
            opacity="0.95"
          />
          <path
            d="M 200 16 A 184 184 0 0 1 318 72"
            fill="none"
            stroke="#ffffff"
            strokeWidth="2"
            strokeLinecap="round"
            opacity="0.45"
          />
        </g>
      </g>

      <g className="elia-splash__svg-ring elia-splash__svg-ring--mid" opacity=".45">
        {[...Array(60)].map((_, i) => {
          const angle = i * 6;
          const len = i % 5 === 0 ? 12 : 6;
          const r1 = 170;
          const r2 = r1 + len;
          const rad = (angle * Math.PI) / 180;
          return (
            <line
              key={i}
              x1={200 + Math.cos(rad) * r1}
              y1={200 + Math.sin(rad) * r1}
              x2={200 + Math.cos(rad) * r2}
              y2={200 + Math.sin(rad) * r2}
              stroke="#5ee8ff"
              strokeWidth="1"
            />
          );
        })}
      </g>

      <g className={`elia-splash__svg-ring elia-splash__svg-ring--mid elia-splash__svg-ring--speed-${Math.min(phase, 3)}`}>
        <circle
          cx="200"
          cy="200"
          r="148"
          fill="none"
          stroke="url(#eliaHudMix)"
          strokeWidth="2"
          strokeDasharray="12 10"
          opacity=".55"
        />
      </g>

      <g className="elia-splash__svg-ring elia-splash__svg-ring--inner" opacity=".45">
        <path d="M110 170 A95 95 0 0 1 170 110" stroke="url(#eliaHudCyan)" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M290 230 A95 95 0 0 1 230 290" stroke="url(#eliaHudMagenta)" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M170 290 A95 95 0 0 1 110 230" stroke="url(#eliaHudCyan)" strokeWidth="1.5" fill="none" />
      </g>

      <g opacity=".45">
        <line x1="200" y1="118" x2="200" y2="282" stroke="#00d2ff" strokeWidth="1" />
        <line x1="118" y1="200" x2="282" y2="200" stroke="#00d2ff" strokeWidth="1" />
      </g>

      <g>
        {[30, 110, 205, 300].map((deg) => {
          const rad = (deg * Math.PI) / 180;
          return (
            <circle
              key={deg}
              cx={200 + Math.cos(rad) * 168}
              cy={200 + Math.sin(rad) * 168}
              r="3"
              fill="#00d2ff"
            />
          );
        })}
      </g>

      <g className="elia-splash__circuit-side" opacity=".35">
        <path d="M-40 170 H40 L70 145 H120" stroke="#00d2ff" fill="none" strokeWidth="1" />
        <rect x="118" y="143" width="4" height="4" fill="#00d2ff" />
        <path d="M-10 240 H55 L80 265 H115" stroke="#8b5cf6" fill="none" strokeWidth="1" />
        <circle cx="115" cy="265" r="2" fill="#8b5cf6" />
        <path d="M440 170 H360 L330 145 H280" stroke="#00d2ff" fill="none" strokeWidth="1" />
        <rect x="278" y="143" width="4" height="4" fill="#00d2ff" />
        <path d="M410 240 H345 L320 265 H285" stroke="#ec4899" fill="none" strokeWidth="1" />
        <circle cx="285" cy="265" r="2" fill="#ec4899" />
      </g>
    </svg>
  );
}
