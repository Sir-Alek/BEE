import React, { useMemo, useState } from "react";
import { publishBddFeature, testReqPublishTarget } from "../../api";
import { BDD_PUBLISH_TARGETS, extractFeatureName } from "../../connectorDefaults";
import { useConnectorContext } from "../../context/ConnectorContext";
import type { BddPublishTarget } from "../../types";

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

  const fieldStyle: React.CSSProperties = {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: `1px solid ${c.inputBorder}`,
    background: c.inputBg,
    color: c.text,
    fontSize: 14,
  };

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
      <select value={target} onChange={(e) => setTarget(e.target.value as BddPublishTarget)} style={fieldStyle}>
        {BDD_PUBLISH_TARGETS.map((t) => (
          <option key={t.id} value={t.id}>
            {t.label}
          </option>
        ))}
      </select>

      {target === "jira_vanilla" || target === "jira_xray" ? (
        <input
          placeholder={target === "jira_xray" ? "Issue key (opcional)" : "Issue key (ej. QA-104)"}
          value={issueKey}
          onChange={(e) => setIssueKey(e.target.value)}
          style={fieldStyle}
        />
      ) : null}

      {target === "value_edge" ? (
        <input
          placeholder="ID story / requerimiento VE"
          value={requirementId}
          onChange={(e) => setRequirementId(e.target.value)}
          style={fieldStyle}
        />
      ) : null}

      {target === "azure_devops" ? (
        <input
          placeholder="Work item ID"
          value={workItemId}
          onChange={(e) => setWorkItemId(e.target.value)}
          style={fieldStyle}
        />
      ) : null}

      {target === "git" ? (
        <>
          <input placeholder="Ruta relativa (opcional)" value={filePath} onChange={(e) => setFilePath(e.target.value)} style={fieldStyle} />
          <input placeholder="Rama" value={branch} onChange={(e) => setBranch(e.target.value)} style={fieldStyle} />
          <input
            placeholder="Mensaje de commit (opcional)"
            value={commitMessage}
            onChange={(e) => setCommitMessage(e.target.value)}
            style={fieldStyle}
          />
        </>
      ) : null}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        <button
          type="button"
          disabled={busy}
          onClick={() => void handleTest()}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: c.btnGhostBg,
            color: c.text,
            border: `1px solid ${c.btnGhostBorder}`,
            cursor: busy ? "wait" : "pointer",
          }}
        >
          Probar destino
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void handlePublish()}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: c.primary,
            color: c.primaryFg,
            border: "none",
            cursor: busy ? "wait" : "pointer",
          }}
        >
          Publicar
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onSkip}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: c.btnGhostBg,
            color: c.text,
            border: `1px solid ${c.btnGhostBorder}`,
            cursor: "pointer",
          }}
        >
          Continuar sin publicar
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onDone}
          style={{
            padding: "10px 14px",
            borderRadius: 10,
            background: c.primary,
            color: c.primaryFg,
            border: "none",
            cursor: "pointer",
            fontWeight: 700,
          }}
        >
          Finalizar y continuar job
        </button>
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
