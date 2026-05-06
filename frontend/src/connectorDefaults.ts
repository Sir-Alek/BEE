import type { EliaConnectorProfile, EliaJiraCreds, EliaValueEdgeCreds } from "./types";

export const ELIA_CONNECTORS_LS_KEY = "elia_connectors_v1";

export function emptyJiraCreds(): EliaJiraCreds {
  return { url: "", email: "", api_token: "" };
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
  };
}

export function newConnectorProfile(n: number): EliaConnectorProfile {
  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `p-${Date.now()}-${Math.random()}`;
  return {
    id,
    name: `Perfil ${n}`,
    jira: emptyJiraCreds(),
    value_edge: emptyValueEdgeCreds(),
  };
}
