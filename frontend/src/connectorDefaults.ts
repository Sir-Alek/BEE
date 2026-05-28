import type {
  BddPublishTarget,
  EliaAzureDevOpsCreds,
  EliaConnectorProfile,
  EliaGitCreds,
  EliaJiraCreds,
  EliaValueEdgeCreds,
} from "./types";

export const ELIA_CONNECTORS_LS_KEY = "elia_connectors_v2";

export function emptyJiraCreds(): EliaJiraCreds {
  return {
    url: "",
    email: "",
    api_token: "",
    mode: "vanilla",
    project_key: "",
    xray_base_url: "",
    target_field: "description",
    default_issue_key: "",
  };
}

export function emptyValueEdgeCreds(): EliaValueEdgeCreds {
  return {
    url: "",
    shared_space: "",
    workspace: "",
    tech_preview_flag: "true",
    login: "",
    user: "",
    password: "",
    default_requirement_id: "",
  };
}

export function emptyGitCreds(): EliaGitCreds {
  return {
    provider: "github",
    repo_url: "",
    branch: "main",
    base_path: "features/",
    token: "",
  };
}

export function emptyAzureDevOpsCreds(): EliaAzureDevOpsCreds {
  return {
    org: "",
    project: "",
    pat: "",
    default_work_item_id: "",
    target_field: "System.Description",
  };
}

export function normalizeConnectorProfile(profile: Partial<EliaConnectorProfile> & { id: string; name: string }): EliaConnectorProfile {
  return {
    id: profile.id,
    name: profile.name,
    jira: { ...emptyJiraCreds(), ...(profile.jira ?? {}) },
    value_edge: { ...emptyValueEdgeCreds(), ...(profile.value_edge ?? {}) },
    git: { ...emptyGitCreds(), ...(profile.git ?? {}) },
    azure_devops: { ...emptyAzureDevOpsCreds(), ...(profile.azure_devops ?? {}) },
  };
}

export function newConnectorProfile(n: number): EliaConnectorProfile {
  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `p-${Date.now()}-${Math.random()}`;
  return normalizeConnectorProfile({
    id,
    name: `Perfil ${n}`,
    jira: emptyJiraCreds(),
    value_edge: emptyValueEdgeCreds(),
    git: emptyGitCreds(),
    azure_devops: emptyAzureDevOpsCreds(),
  });
}

export const BDD_PUBLISH_TARGETS: { id: BddPublishTarget; label: string }[] = [
  { id: "local_file", label: "Guardar .feature local" },
  { id: "git", label: "Commit a Git" },
  { id: "jira_vanilla", label: "Jira (descripción)" },
  { id: "jira_xray", label: "Jira + Xray" },
  { id: "value_edge", label: "ValueEdge bdd_spec" },
  { id: "azure_devops", label: "Azure DevOps Work Item" },
];

export function extractFeatureName(gherkin: string): string {
  for (const line of gherkin.split(/\r?\n/)) {
    const m = /^\s*Feature:\s*(.+)$/i.exec(line);
    if (m?.[1]?.trim()) return m[1].trim();
  }
  return "Feature";
}
