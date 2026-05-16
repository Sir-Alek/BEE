import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "elia_theme";
const BC_NAME = "elia-theme";

function migrateLegacyThemePrefs(): void {
  try {
    const legacy = localStorage.getItem("bee_theme");
    if (legacy && !localStorage.getItem(STORAGE_KEY)) {
      localStorage.setItem(STORAGE_KEY, legacy);
    }
    if (legacy) localStorage.removeItem("bee_theme");
  } catch {
    // ignore
  }
}

export type EliaPalette = {
  pageBg: string;
  surface: string;
  border: string;
  text: string;
  muted: string;
  primary: string;
  primaryFg: string;
  errorBg: string;
  errorBorder: string;
  errorTitle: string;
  errorBody: string;
  successBg: string;
  successBorder: string;
  successTitle: string;
  successBody: string;
  successHint: string;
  hintBg: string;
  hintBorder: string;
  hintText: string;
  warnBg: string;
  warnBorder: string;
  warnText: string;
  licOkBg: string;
  licOkBorder: string;
  licWarnBg: string;
  licWarnBorder: string;
  neutralBg: string;
  processingBg: string;
  processingBorder: string;
  processingText: string;
  chromeBg: string;
  chromeHint: string;
  inputBg: string;
  inputBorder: string;
  btnGhostBg: string;
  btnGhostText: string;
  btnGhostBorder: string;
  stickyBarBg: string;
  codeBg: string;
  msgInfoBg: string;
  msgInfoBorder: string;
  msgInfoText: string;
  msgWarnBg: string;
  msgWarnBorder: string;
  msgWarnText: string;
  msgErrBg: string;
  msgErrBorder: string;
  msgErrText: string;
  actionDesc: string;
  shadow: string;
  buttonDisabledBg: string;
};

const LIGHT: EliaPalette = {
  pageBg: "#f9fafb",
  surface: "#ffffff",
  border: "#e5e7eb",
  text: "#111827",
  muted: "#6b7280",
  primary: "#0ea5e9",
  primaryFg: "#ffffff",
  errorBg: "#fef2f2",
  errorBorder: "#fecaca",
  errorTitle: "#b91c1c",
  errorBody: "#991b1b",
  successBg: "#ecfdf5",
  successBorder: "#bbf7d0",
  successTitle: "#166534",
  successBody: "#065f46",
  successHint: "#047857",
  hintBg: "#eff6ff",
  hintBorder: "#bfdbfe",
  hintText: "#1e3a8a",
  warnBg: "#fffbeb",
  warnBorder: "#fde68a",
  warnText: "#92400e",
  licOkBg: "#f0fdf4",
  licOkBorder: "#bbf7d0",
  licWarnBg: "#fffbeb",
  licWarnBorder: "#fde68a",
  neutralBg: "#f9fafb",
  processingBg: "#f3f4f6",
  processingBorder: "#e5e7eb",
  processingText: "#374151",
  chromeBg: "#ffffff",
  chromeHint: "#6b7280",
  inputBg: "#ffffff",
  inputBorder: "#d1d5db",
  btnGhostBg: "#ffffff",
  btnGhostText: "#111827",
  btnGhostBorder: "#d1d5db",
  stickyBarBg: "#ffffff",
  codeBg: "#f3f4f6",
  msgInfoBg: "#eff6ff",
  msgInfoBorder: "#bfdbfe",
  msgInfoText: "#1e3a8a",
  msgWarnBg: "#fffbeb",
  msgWarnBorder: "#fde68a",
  msgWarnText: "#92400e",
  msgErrBg: "#fef2f2",
  msgErrBorder: "#fecaca",
  msgErrText: "#991b1b",
  actionDesc: "#4b5563",
  shadow: "0 1px 2px rgba(0,0,0,0.03)",
  buttonDisabledBg: "#94a3b8",
};

const DARK: EliaPalette = {
  pageBg: "#0b1220",
  surface: "#111827",
  border: "#334155",
  text: "#e5e7eb",
  muted: "#94a3b8",
  primary: "#38bdf8",
  primaryFg: "#0f172a",
  errorBg: "#450a0a",
  errorBorder: "#7f1d1d",
  errorTitle: "#fecaca",
  errorBody: "#fca5a5",
  successBg: "#052e16",
  successBorder: "#166534",
  successTitle: "#bbf7d0",
  successBody: "#86efac",
  successHint: "#4ade80",
  hintBg: "#172554",
  hintBorder: "#1e40af",
  hintText: "#bfdbfe",
  warnBg: "#422006",
  warnBorder: "#b45309",
  warnText: "#fde68a",
  licOkBg: "#052e16",
  licOkBorder: "#166534",
  licWarnBg: "#422006",
  licWarnBorder: "#b45309",
  neutralBg: "#0f172a",
  processingBg: "#1e293b",
  processingBorder: "#334155",
  processingText: "#cbd5e1",
  chromeBg: "#111827",
  chromeHint: "#94a3b8",
  inputBg: "#0f172a",
  inputBorder: "#475569",
  btnGhostBg: "#1e293b",
  btnGhostText: "#e5e7eb",
  btnGhostBorder: "#475569",
  stickyBarBg: "#111827",
  codeBg: "#1e293b",
  msgInfoBg: "#172554",
  msgInfoBorder: "#1e40af",
  msgInfoText: "#bfdbfe",
  msgWarnBg: "#422006",
  msgWarnBorder: "#b45309",
  msgWarnText: "#fde68a",
  msgErrBg: "#450a0a",
  msgErrBorder: "#991b1b",
  msgErrText: "#fecaca",
  actionDesc: "#cbd5e1",
  shadow: "0 1px 2px rgba(0,0,0,0.25)",
  buttonDisabledBg: "#475569",
};

type Ctx = {
  dark: boolean;
  setDark: (v: boolean) => void;
  toggle: () => void;
  c: EliaPalette;
};

const ThemeCtx = createContext<Ctx | null>(null);

export function EliaThemeProvider({ children }: { children: React.ReactNode }) {
  const [dark, setDarkState] = useState<boolean>(() => {
    migrateLegacyThemePrefs();
    try {
      const v = localStorage.getItem(STORAGE_KEY);
      return v === "dark";
    } catch {
      return false;
    }
  });

  const setDark = useCallback((v: boolean) => {
    setDarkState(v);
    try {
      localStorage.setItem(STORAGE_KEY, v ? "dark" : "light");
    } catch {
      // ignore
    }
    try {
      document.documentElement.setAttribute("data-elia-theme", v ? "dark" : "light");
    } catch {
      // ignore
    }
    try {
      const bc = new BroadcastChannel(BC_NAME);
      bc.postMessage({ type: "elia_theme", dark: v });
      bc.close();
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    try {
      document.documentElement.setAttribute("data-elia-theme", dark ? "dark" : "light");
    } catch {
      // ignore
    }
  }, [dark]);

  useEffect(() => {
    let bc: BroadcastChannel | null = null;
    try {
      bc = new BroadcastChannel(BC_NAME);
      bc.onmessage = (ev: MessageEvent) => {
        if (ev.data?.type === "elia_theme" && typeof ev.data?.dark === "boolean") {
          setDarkState(ev.data.dark);
          try {
            localStorage.setItem(STORAGE_KEY, ev.data.dark ? "dark" : "light");
          } catch {
            // ignore
          }
          try {
            document.documentElement.setAttribute("data-elia-theme", ev.data.dark ? "dark" : "light");
          } catch {
            // ignore
          }
        }
      };
    } catch {
      // ignore
    }
    return () => {
      try {
        bc?.close();
      } catch {
        // ignore
      }
    };
  }, []);

  const c = useMemo(() => (dark ? DARK : LIGHT), [dark]);
  const toggle = useCallback(() => setDark(!dark), [dark, setDark]);

  const value = useMemo(() => ({ dark, setDark, toggle, c }), [dark, setDark, toggle, c]);

  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

export function useEliaTheme(): Ctx {
  const v = useContext(ThemeCtx);
  if (!v) throw new Error("useEliaTheme must be used within EliaThemeProvider");
  return v;
}

/** Append to job URLs so a new tab applies theme before first paint logic runs. */
export function themeQuerySuffix(): string {
  migrateLegacyThemePrefs();
  try {
    const d = localStorage.getItem(STORAGE_KEY) === "dark";
    return `&theme=${d ? "dark" : "light"}`;
  } catch {
    return "&theme=light";
  }
}

/** Call once on app load (job tab) to honor ?theme=dark|light */
export function applyThemeFromUrl(): void {
  try {
    const t = new URLSearchParams(window.location.search).get("theme");
    if (t === "dark" || t === "light") {
      localStorage.setItem(STORAGE_KEY, t === "dark" ? "dark" : "light");
      document.documentElement.setAttribute("data-elia-theme", t);
    }
  } catch {
    // ignore
  }
}
