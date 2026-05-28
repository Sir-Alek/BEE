export type GeneratedFileEntry = {
  path: string;
  label?: string;
  preview?: string;
};

export type ConversionResultPayload = {
  project_dir?: string;
  output_dir?: string;
  generated_files?: GeneratedFileEntry[];
};

/** Metadatos opcionales del backend para controles del prompt (regresar, sugerencias, etc.). */
export type PromptControlPayload = {
  allow_back?: boolean;
  suggested?: string;
};

export function promptAllowsBack(payload: unknown): boolean {
  return Boolean(
    payload &&
      typeof payload === "object" &&
      "allow_back" in payload &&
      (payload as PromptControlPayload).allow_back,
  );
}

export type ActivePrompt =
  | {
      prompt_id: string;
      type: "pick_project";
      title: string;
      message: string;
      options: { value: string; label: string }[];
      actions: null;
      payload?: PromptControlPayload | null;
    }
  | {
      prompt_id: string;
      type: "pick_script";
      title: string;
      message: string;
      options: { value: string; label: string }[];
      actions: null;
      payload?: PromptControlPayload | null;
    }
  | {
      prompt_id: string;
      type: "pick_actions";
      title: string;
      message: string;
      options: null;
      actions: { type: string; description: string; original_line: string }[];
      payload?: PromptControlPayload | null;
    }
  | {
      prompt_id: string;
      type: "yes_no";
      title: string;
      message: string;
      options: null;
      actions: null;
    }
  | {
      prompt_id: string;
      type: "yes_no_cancel";
      title: string;
      message: string;
      options: null;
      actions: null;
    }
  | {
      prompt_id: string;
      type: "input_text";
      title: string;
      message: string;
      options: null;
      actions: null;
      payload?: PromptControlPayload | null;
    }
  | {
      prompt_id: string;
      type: "message_ack";
      title: string;
      message: string;
      severity: "info" | "warning" | "error";
      payload?: ConversionResultPayload | null;
      options: null;
      actions: null;
    }
  | {
      prompt_id: string;
      type: "bdd_preview";
      title: string;
      message: string;
      payload: {
        feature_text: string;
        attempt: number;
        max_attempts: number;
        script_excerpt: string;
        can_manual: boolean;
      };
      options: null;
      actions: null;
    }
  | {
      prompt_id: string;
      type: "pick_conversion_mode";
      title: string;
      message: string;
      options: { value: string; label: string }[];
      actions: null;
    }
  | {
      prompt_id: string;
      type: "pick_scripts_multi";
      title: string;
      message: string;
      options: null;
      actions: { type: string; description: string; original_line: string }[];
    }
  | {
      prompt_id: string;
      type: "recording_options";
      title: string;
      message: string;
      payload: {
        options: { key: string; label: string; default?: boolean }[];
      };
      options: null;
      actions: null;
    }
  | {
      prompt_id: string;
      type: "grouped_feature_review";
      title: string;
      message: string;
      payload?: {
        feature_text?: string;
        script_names?: string[];
        background_count?: number;
      };
      options: null;
      actions: null;
    };

export type EliaJiraCreds = {
  url: string;
  email: string;
  api_token: string;
  mode: "vanilla" | "xray";
  project_key: string;
  xray_base_url: string;
  target_field: string;
  default_issue_key: string;
};

export type EliaValueEdgeCreds = {
  url: string;
  shared_space: string;
  workspace: string;
  tech_preview_flag: string;
  login: string;
  user: string;
  password: string;
  default_requirement_id: string;
};

export type EliaGitCreds = {
  provider: "github" | "gitlab" | "azure_repos";
  repo_url: string;
  branch: string;
  base_path: string;
  token: string;
};

export type EliaAzureDevOpsCreds = {
  org: string;
  project: string;
  pat: string;
  default_work_item_id: string;
  target_field: string;
};

export type EliaConnectorProfile = {
  id: string;
  name: string;
  jira: EliaJiraCreds;
  value_edge: EliaValueEdgeCreds;
  git: EliaGitCreds;
  azure_devops: EliaAzureDevOpsCreds;
};

export type EliaConnectorsDocument = {
  version: 1 | 2;
  profiles: EliaConnectorProfile[];
};

export type BddPublishTarget =
  | "local_file"
  | "git"
  | "jira_vanilla"
  | "jira_xray"
  | "value_edge"
  | "azure_devops";

export type ModulesStatus = {
  mobile_recording: boolean;
  legacy_recording: boolean;
  doc_to_bdd: boolean;
  api_testing: boolean;
  api_limits?: {
    max_load_users: number;
    max_load_spawn_rate: number;
    max_suite_scenarios: number;
    evidence_opt_in: boolean;
  };
};

export type LoadedDoc = {
  name: string;
  path: string;
  ext: string;
};

export type ScenarioRef = {
  feature_file: string;
  scenario_name: string;
  line: string;
};

export type RecordingRef = {
  project: string;
  file_name: string;
  file_path: string;
  platform: string;
  label: string;
};

