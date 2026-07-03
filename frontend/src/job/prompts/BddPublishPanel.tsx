import React, { useMemo, useState } from "react";
import { publishBddFeature, testReqPublishTarget } from "../../api";
import { BDD_PUBLISH_TARGETS, extractFeatureName } from "../../connectorDefaults";
import { useConnectorContext } from "../../context/ConnectorContext";
import type { BddPublishTarget } from "../../types";
import { EliaButton } from "../../components/ui";

type Props = {
  c: Record<string, string>;
  gherkinText: string;
  onSkip: () => void;
  onDone: () => void;
};

export function BddPublishPanel(props: Props) {
  const { c, gherkinText, onSkip, onDone } = props;
  const { connectorProfiles, reqConnectorProfileId } = useConnectorContext();
  const profile = connectorProfiles.find((x) => x.id === reqConnectorProfileId);

  const [target, setTarget] = useState<BddPublishTarget>("local_file");
  const [issueKey, setIssueKey] = useState(profile?.jira.default_issue_key ?? "");
  const [requirementId, setRequirementId] = useState(profile?.value_edge.default_requirement_id ?? "");
  const [workItemId, setWorkItemId] = useState(profile?.azure_devops.default_work_item_id ?? "");
  const [filePath, setFilePath] = useState("");
  const [branch, setBranch] = useState(profile?.git.branch ?? "main");
  const [commitMessage, setCommitMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const featureName = useMemo(() => extractFeatureName(gherkinText), [gherkinText]);

  const fieldClass = "elia-input";

  async function handlePublish() {
    if (!reqConnectorProfileId) {
      setStatusMsg("Selecciona un perfil de conector en Inicio antes de publicar.");
      return;
    }
    setBusy(true);
    setStatusMsg(null);
    try {
      const r = await publishBddFeature({
        target,
        profile_id: reqConnectorProfileId,
        gherkin_text: gherkinText,
        feature_name: featureName,
        issue_key: issueKey,
        requirement_id: requirementId,
        work_item_id: workItemId,
        file_path: filePath,
        branch,
        commit_message: commitMessage,
      });
      const extra = r.url ? ` · ${r.url}` : "";
      setStatusMsg(`✓ ${r.message}${extra}`);
    } catch (err: unknown) {
      setStatusMsg(String((err as Error)?.message ?? err));
    } finally {
      setBusy(false);
    }
  }

  async function handleTest() {
    if (!reqConnectorProfileId) {
      setStatusMsg("Perfil de conector no seleccionado.");
      return;
    }
    setBusy(true);
    setStatusMsg(null);
    try {
      const r = await testReqPublishTarget({ target, profile_id: reqConnectorProfileId });
      setStatusMsg(r.ok ? `✓ ${r.message}` : r.message);
    } catch (err: unknown) {
      setStatusMsg(String((err as Error)?.message ?? err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ fontSize: 13, color: c.muted }}>
        Escenario revisado. Opcionalmente publica el Gherkin en un destino ALM/Git antes de continuar el job.
        Perfil activo: <strong>{profile?.name ?? "— ninguno —"}</strong>
      </div>

      <label style={{ fontSize: 13, fontWeight: 600 }}>Destino</label>
      <select value={target} onChange={(e) => setTarget(e.target.value as BddPublishTarget)} className={fieldClass} style={{ width: "100%" }}>
        {BDD_PUBLISH_TARGETS.map((t) => (
          <option key={t.id} value={t.id}>
            {t.label}
          </option>
        ))}
      </select>

      {target === "jira_vanilla" || target === "jira_xray" ? (
        <input
          className={fieldClass}
          placeholder={target === "jira_xray" ? "Issue key (opcional)" : "Issue key (ej. QA-104)"}
          value={issueKey}
          onChange={(e) => setIssueKey(e.target.value)}
          style={{ width: "100%" }}
        />
      ) : null}

      {target === "value_edge" ? (
        <input
          className={fieldClass}
          placeholder="ID story / requerimiento VE"
          value={requirementId}
          onChange={(e) => setRequirementId(e.target.value)}
          style={{ width: "100%" }}
        />
      ) : null}

      {target === "azure_devops" ? (
        <input
          className={fieldClass}
          placeholder="Work item ID"
          value={workItemId}
          onChange={(e) => setWorkItemId(e.target.value)}
          style={{ width: "100%" }}
        />
      ) : null}

      {target === "git" ? (
        <>
          <input className={fieldClass} placeholder="Ruta relativa (opcional)" value={filePath} onChange={(e) => setFilePath(e.target.value)} style={{ width: "100%" }} />
          <input className={fieldClass} placeholder="Rama" value={branch} onChange={(e) => setBranch(e.target.value)} style={{ width: "100%" }} />
          <input
            className={fieldClass}
            placeholder="Mensaje de commit (opcional)"
            value={commitMessage}
            onChange={(e) => setCommitMessage(e.target.value)}
            style={{ width: "100%" }}
          />
        </>
      ) : null}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        <EliaButton variant="ghost" size="sm" disabled={busy} onClick={() => void handleTest()}>
          Probar destino
        </EliaButton>
        <EliaButton variant="primary" size="sm" disabled={busy} onClick={() => void handlePublish()}>
          Publicar
        </EliaButton>
        <EliaButton variant="ghost" size="sm" disabled={busy} onClick={onSkip}>
          Continuar sin publicar
        </EliaButton>
        <EliaButton variant="primary" size="sm" disabled={busy} onClick={onDone}>
          Finalizar y continuar job
        </EliaButton>
      </div>

      {statusMsg ? (
        <div
          style={{
            fontSize: 13,
            color: c.text,
            background: c.hintBg,
            border: `1px solid ${c.hintBorder}`,
            borderRadius: 10,
            padding: 10,
            whiteSpace: "pre-wrap",
          }}
        >
          {statusMsg}
        </div>
      ) : null}
    </div>
  );
}
