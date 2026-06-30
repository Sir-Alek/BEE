import React from "react";
import type { EntitlementBanner as BannerKind } from "../app/entitlementPhase";
import { LoadingStatusRow } from "./LoadingStatusRow";

const COPY: Record<BannerKind, string | null> = {
  verifying: "Comprobando tu plan…",
  modules_loading: "Cargando configuración de módulos…",
  offline: "Modo desconectado: usando última configuración conocida.",
  none: null,
};

type Props = {
  c: Record<string, string>;
  banner: BannerKind;
  onDismissOffline?: () => void;
  offlineDismissed?: boolean;
};

export function EntitlementBanner(props: Props) {
  const { c, banner, onDismissOffline, offlineDismissed } = props;
  if (banner === "none" || (banner === "offline" && offlineDismissed)) return null;
  const text = COPY[banner];
  if (!text) return null;

  const isOffline = banner === "offline";

  if (isOffline) {
    return (
      <div
        role="status"
        data-testid={`elia-entitlement-banner-${banner}`}
        style={{
          background: c.neutralBg,
          border: `1px solid ${c.border}`,
          color: c.hintText,
          padding: "10px 14px",
          borderRadius: 10,
          marginBottom: 14,
          fontSize: 13,
          display: "flex",
          alignItems: "center",
          gap: 8,
          lineHeight: 1.45,
        }}
      >
        <span style={{ flex: 1 }}>{text}</span>
        {onDismissOffline ? (
          <button
            type="button"
            onClick={onDismissOffline}
            style={{
              border: "none",
              background: "transparent",
              color: c.muted,
              cursor: "pointer",
              fontSize: 12,
              padding: "2px 6px",
            }}
          >
            Ocultar
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <LoadingStatusRow
      c={c}
      text={text ?? ""}
      testId={`elia-entitlement-banner-${banner}`}
      loading
    />
  );
}
