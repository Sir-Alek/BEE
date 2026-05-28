import React, { useState } from "react";
import { sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { cancelJobFlow } from "../promptNav";
import { BddPublishPanel } from "./BddPublishPanel";

type Props = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "bdd_preview" }>;
  bddPreviewText: string;
  setBddPreviewText: (v: string) => void;
};

export function BddPreviewPrompt(props: Props) {
  const { c, jobId, activePrompt: ap, bddPreviewText, setBddPreviewText } = props;
  const [phase, setPhase] = useState<"review" | "publish">("review");

  if (!ap.payload) return null;

  async function acceptJob() {
    const orig = String(ap.payload?.feature_text ?? "");
    const edited = bddPreviewText.trim() !== orig.trim();
    await sendPromptResponse({
      jobId,
      promptId: ap.prompt_id,
      answer: { action: "accept", feature_text: bddPreviewText, edited },
    });
  }

  if (phase === "publish") {
    return (
      <BddPublishPanel
        c={c}
        gherkinText={bddPreviewText}
        onSkip={() => void acceptJob()}
        onDone={() => void acceptJob()}
      />
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ fontSize: 13, color: c.muted }}>
        Intento {ap.payload.attempt} de {ap.payload.max_attempts}.{" "}
        {ap.payload.can_manual
          ? "Puedes editar el escenario a mano o usar la versión heurística."
          : "Revisa el texto; puedes aceptarlo o pedir otra versión con IA."}
      </div>
      {ap.payload.script_excerpt?.trim() ? (
        <div>
          <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>Extracto del script (referencia)</div>
          <textarea
            readOnly
            value={ap.payload.script_excerpt}
            style={{
              width: "100%",
              minHeight: 120,
              padding: 10,
              borderRadius: 10,
              border: `1px solid ${c.border}`,
              fontFamily: "ui-monospace, monospace",
              fontSize: 12,
              background: c.codeBg,
              color: c.text,
            }}
          />
        </div>
      ) : null}
      <div>
        <div style={{ fontSize: 12, color: c.muted, marginBottom: 6 }}>Feature (.feature)</div>
        <textarea
          value={bddPreviewText}
          onChange={(e) => setBddPreviewText(e.target.value)}
          readOnly={!ap.payload.can_manual}
          style={{
            width: "100%",
            minHeight: 220,
            padding: 10,
            borderRadius: 10,
            border: `1px solid ${c.inputBorder}`,
            fontFamily: "ui-monospace, monospace",
            fontSize: 13,
            background: ap.payload.can_manual ? c.inputBg : c.codeBg,
            color: c.text,
          }}
        />
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        <button
          type="button"
          onClick={() => setPhase("publish")}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: c.primary,
            color: c.primaryFg,
            border: "none",
            cursor: "pointer",
          }}
        >
          {ap.payload.can_manual ? "Aceptar escenario" : "Aceptar"}
        </button>
        {!ap.payload.can_manual ? (
          <button
            type="button"
            onClick={async () => {
              await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: { action: "reject" } });
            }}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              background: c.btnGhostBg,
              color: c.text,
              border: `1px solid ${c.btnGhostBorder}`,
              cursor: "pointer",
            }}
          >
            Rechazar (regenerar)
          </button>
        ) : (
          <button
            type="button"
            onClick={async () => {
              await sendPromptResponse({ jobId, promptId: ap.prompt_id, answer: { action: "use_heuristic" } });
            }}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              background: c.btnGhostBg,
              color: c.text,
              border: `1px solid ${c.btnGhostBorder}`,
              cursor: "pointer",
            }}
          >
            Usar generación heurística
          </button>
        )}
        <button
          type="button"
          onClick={() => {
            void cancelJobFlow(jobId);
          }}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: c.btnGhostBg,
            color: c.muted,
            border: `1px solid ${c.btnGhostBorder}`,
            cursor: "pointer",
          }}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
