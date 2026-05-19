export type ActivePrompt =
  | {
      prompt_id: string;
      type: "pick_project";
      title: string;
      message: string;
      options: { value: string; label: string }[];
      actions: null;
    }
  | {
      prompt_id: string;
      type: "pick_script";
      title: string;
      message: string;
      options: { value: string; label: string }[];
      actions: null;
    }
  | {
      prompt_id: string;
      type: "pick_actions";
      title: string;
      message: string;
      options: null;
      actions: { type: string; description: string; original_line: string }[];
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
    }
  | {
      prompt_id: string;
      type: "message_ack";
      title: string;
      message: string;
      severity: "info" | "warning" | "error";
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
      type: string;
      title: string;
      message: string;
      options: any;
      actions: any;
    };

export type EliaJiraCreds = {
  url: string;
  email: string;
  api_token: string;
};

export type EliaValueEdgeCreds = {
  url: string;
  shared_space: string;
  workspace: string;
  tech_preview_flag: string;
  login: string;
  user: string;
  password: string;
};

export type EliaConnectorProfile = {
  id: string;
  name: string;
  jira: EliaJiraCreds;
  value_edge: EliaValueEdgeCreds;
};

export type EliaConnectorsDocument = {
  version: 1;
  profiles: EliaConnectorProfile[];
};

export type ModulesStatus = {
  mobile_recording: boolean;
  legacy_recording: boolean;
  doc_to_bdd: boolean;
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

