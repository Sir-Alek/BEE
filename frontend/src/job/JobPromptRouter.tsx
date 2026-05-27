import React from "react";
import type { ActivePrompt } from "../types";
import { JobPromptShell } from "./prompts/JobPromptShell";
import { PickConversionModePrompt } from "./prompts/PickConversionModePrompt";
import { PickOptionsPrompt } from "./prompts/PickOptionsPrompt";
import { PickActionsPrompt, PickScriptsMultiPrompt } from "./prompts/PickActionsPrompt";
import { RecordingOptionsPrompt } from "./prompts/RecordingOptionsPrompt";
import { YesNoPrompt } from "./prompts/YesNoPrompt";
import { BddPreviewPrompt } from "./prompts/BddPreviewPrompt";
import { GroupedFeatureReviewPrompt } from "./prompts/GroupedFeatureReviewPrompt";
import { MessageAckPrompt } from "./prompts/MessageAckPrompt";
import { InputTextPrompt } from "./prompts/InputTextPrompt";
import { PromptNavButtons } from "./prompts/PromptNavButtons";
import type { JobProgressState } from "./useJobProgress";
import { promptAllowsBack } from "../types";

type Props = {
  c: Record<string, string>;
  jobId: string;
  job: JobProgressState | null;
  activePrompt: ActivePrompt;
  textValue: string;
  setTextValue: (v: string) => void;
  bddPreviewText: string;
  setBddPreviewText: (v: string) => void;
};

export function JobPromptRouter(props: Props) {
  const { c, jobId, job, activePrompt, textValue, setTextValue, bddPreviewText, setBddPreviewText } = props;

  const body = (() => {
    switch (activePrompt.type) {
      case "pick_conversion_mode":
        return <PickConversionModePrompt c={c} jobId={jobId} activePrompt={activePrompt} />;
      case "pick_project":
      case "pick_script":
        return <PickOptionsPrompt c={c} jobId={jobId} activePrompt={activePrompt} />;
      case "pick_actions":
        return <PickActionsPrompt c={c} jobId={jobId} activePrompt={activePrompt} />;
      case "pick_scripts_multi":
        return <PickScriptsMultiPrompt c={c} jobId={jobId} activePrompt={activePrompt} />;
      case "yes_no":
      case "yes_no_cancel":
        return <YesNoPrompt c={c} jobId={jobId} activePrompt={activePrompt} />;
      case "recording_options":
        return <RecordingOptionsPrompt c={c} jobId={jobId} activePrompt={activePrompt} />;
      case "bdd_preview":
        return (
          <BddPreviewPrompt
            c={c}
            jobId={jobId}
            activePrompt={activePrompt}
            bddPreviewText={bddPreviewText}
            setBddPreviewText={setBddPreviewText}
          />
        );
      case "grouped_feature_review":
        return (
          <GroupedFeatureReviewPrompt
            c={c}
            jobId={jobId}
            activePrompt={activePrompt}
            bddPreviewText={bddPreviewText}
            setBddPreviewText={setBddPreviewText}
          />
        );
      case "message_ack":
        return <MessageAckPrompt c={c} jobId={jobId} activePrompt={activePrompt} job={job} />;
      case "input_text":
        return (
          <InputTextPrompt
            c={c}
            jobId={jobId}
            activePrompt={activePrompt}
            textValue={textValue}
            setTextValue={setTextValue}
          />
        );
      default:
        return null;
    }
  })();

  if (activePrompt.type === "message_ack") {
    return (
      <JobPromptShell c={c} jobId={jobId} activePrompt={activePrompt}>
        {body}
      </JobPromptShell>
    );
  }

  const usesOwnNav =
    activePrompt.type === "input_text" ||
    activePrompt.type === "bdd_preview" ||
    activePrompt.type === "grouped_feature_review";
  const showBack = "payload" in activePrompt && promptAllowsBack(activePrompt.payload);

  return (
    <JobPromptShell c={c} jobId={jobId} activePrompt={activePrompt}>
      {body}
      {!usesOwnNav ? (
        <PromptNavButtons
          c={c}
          jobId={jobId}
          promptId={activePrompt.prompt_id}
          showBack={showBack}
        />
      ) : null}
    </JobPromptShell>
  );
}
