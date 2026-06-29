import React from "react";
import type { EntitlementPhase } from "../app/entitlementPhase";
import {
  getFeatureAccess,
  shouldShowTierUpsell,
  type FeatureAccess,
} from "../app/entitlementPhase";
import type { LicenseState } from "../app/licenseUtils";
import type { FeatureFlags } from "../types";

type Props = {
  c: Record<string, string>;
  phase: EntitlementPhase;
  feature: keyof FeatureFlags;
  features: FeatureFlags;
  license: LicenseState | null;
  showTierUpsell: boolean;
  children: React.ReactNode;
  /** Overlay comercial (UpsellModal trigger area). Solo si access=denied y fase estable. */
  upsellOverlay?: React.ReactNode;
  minHeight?: number | string;
};

function PendingShell(props: { c: Record<string, string>; children: React.ReactNode; minHeight?: number | string }) {
  const { c, children, minHeight } = props;
  return (
    <div style={{ position: "relative", minHeight: minHeight ?? undefined }}>
      <div style={{ opacity: 0.5, pointerEvents: "none" }}>{children}</div>
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          pointerEvents: "none",
        }}
      >
        <span
          style={{
            width: 18,
            height: 18,
            borderRadius: "50%",
            border: `2px solid ${c.border}`,
            borderTopColor: c.primary,
            animation: "elia-spin 0.8s linear infinite",
          }}
        />
      </div>
    </div>
  );
}

export function useFeatureAccess(
  phase: EntitlementPhase,
  feature: keyof FeatureFlags,
  features: FeatureFlags,
  license: LicenseState | null,
  showTierUpsell: boolean,
): { access: FeatureAccess; showUpsell: boolean } {
  const access = getFeatureAccess(phase, feature, features, license);
  const showUpsell = shouldShowTierUpsell(phase, access, showTierUpsell);
  return { access, showUpsell };
}

export function FeatureGate(props: Props) {
  const { c, phase, feature, features, license, showTierUpsell, children, upsellOverlay, minHeight } = props;
  const { access, showUpsell } = useFeatureAccess(phase, feature, features, license, showTierUpsell);

  if (access === "granted") return <>{children}</>;

  if (access === "pending") {
    return <PendingShell c={c} minHeight={minHeight}>{children}</PendingShell>;
  }

  if (showUpsell && upsellOverlay) {
    return (
      <div style={{ position: "relative" }}>
        <div style={{ opacity: 0.45, pointerEvents: "none" }}>{children}</div>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(0,0,0,0.06)",
            borderRadius: 12,
          }}
        >
          {upsellOverlay}
        </div>
      </div>
    );
  }

  return (
    <div style={{ opacity: 0.45, pointerEvents: "none" }}>{children}</div>
  );
}
