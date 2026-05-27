import React from "react";
import { sendPromptResponse } from "../../api";
import type { ActivePrompt } from "../../types";
import { ActionsCheckboxList } from "../jobUiComponents";

type PickActionsProps = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "pick_actions" }>;
};

export function PickActionsPrompt(props: PickActionsProps) {
  const { c, jobId, activePrompt } = props;
  if (!activePrompt.actions) return null;
  return (
    <div>
      <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>Marca las acciones a convertir</div>
      <div style={{ border: `1px solid ${c.border}`, borderRadius: 12, padding: 12, maxHeight: 320, overflow: "auto" }}>
        <ActionsCheckboxList
          c={c}
          promptId={activePrompt.prompt_id}
          actions={activePrompt.actions}
          onSubmit={async (selectedLines) => {
            await sendPromptResponse({
              jobId,
              promptId: activePrompt.prompt_id,
              answer: selectedLines,
            });
          }}
        />
      </div>
    </div>
  );
}

type PickMultiProps = {
  c: Record<string, string>;
  jobId: string;
  activePrompt: Extract<ActivePrompt, { type: "pick_scripts_multi" }>;
};

export function PickScriptsMultiPrompt(props: PickMultiProps) {
  const { c, jobId, activePrompt } = props;
  if (!activePrompt.actions) return null;
  return (
    <div>
      <div style={{ fontSize: 12, color: c.muted, marginBottom: 8 }}>
        Marca al menos 2 grabaciones y pulsa Continuar.
      </div>
      <div style={{ border: `1px solid ${c.border}`, borderRadius: 12, padding: 12, maxHeight: 320, overflow: "auto" }}>
        <ActionsCheckboxList
          c={c}
          promptId={activePrompt.prompt_id}
          actions={activePrompt.actions}
          minSelected={2}
          emptySelectionMessage="Selecciona al menos dos grabaciones para continuar."
          onSubmit={async (selectedLines) => {
            await sendPromptResponse({
              jobId,
              promptId: activePrompt.prompt_id,
              answer: selectedLines,
            });
          }}
        />
      </div>
    </div>
  );
}
