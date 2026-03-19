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
      type: string;
      title: string;
      message: string;
      options: any;
      actions: any;
    };

