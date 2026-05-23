import type React from "react";

export const ELIA_UI_BC = "elia-ui";

/** Avisos de validación en la pantalla principal: se ocultan solos o con ✕ */
export const HOME_ERROR_DISMISS_MS = 8_000;

export const ELIA_LOGO_ICON_STYLE: React.CSSProperties = {
  height: 52,
  width: "auto",
  maxWidth: 100,
  objectFit: "contain",
  flexShrink: 0,
  transform: "scale(1.6)",
  transformOrigin: "left center",
};

export const ELIA_LOGO_LETTERS_STYLE: React.CSSProperties = {
  height: 64,
  width: "auto",
  maxWidth: 100,
  objectFit: "contain",
  flexShrink: 0,
  transform: "scale(2.5)",
  transformOrigin: "left center",
};
