import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  cloneApiScenario,
  createApiProject,
  deleteApiCollection,
  deleteApiScenario,
  deleteApiScenarios,
  executeApiRequest,
  exportApiLoadEvidence,
  exportApiRequestEvidence,
  getApiEnvironment,
  getApiEnvironments,
  getApiProjectConfig,
  getApiProjects,
  getApiScenarioDetail,
  getApiScenarios,
  getApiTrafficCaptures,
  getApiWebOrigin,
  getProjectReportUrl,
  getProjectEvidenceUrl,
  getTestRun,
  importApiTrafficCapture,
  importOpenApiSpec,
  importPostmanCollection,
  loadPreflightApi,
  openProjectFolder,
  runLoadTest,
  saveApiEnvironment,
  saveApiLoadSnapshot,
  saveApiProjectConfig,
  saveApiScenario,
  syncApiEnvironmentFromWeb,
  listApiFlows,
  getApiFlow,
  getJmxImportMeta,
  type JmxImportMeta,
  type JmxImportResult,
} from "../api";
import { ConfirmModal } from "../components/ConfirmModal";
import {
  DataCsvPanel,
  LoadHistoryComparePanel,
  LoadMetricsPanel,
  SuiteHistoryPanel,
  SuiteRunnerPanel,
  type AssertionRow,
  type ExtractorRow,
} from "./ApiAdvancedPanels";
import { RunConsolePanel } from "./RunConsolePanel";
import { ApiPostmanSidebar, type ApiCollectionRow, type ApiScenarioRow } from "./api/ApiPostmanSidebar";
import {
  LoadTestPanel,
  buildSlaPayload,
  buildThinkTimePayload,
  defaultLoadTestSettings,
  validateDistributedLoadSettings,
  type LoadTestSettings,
} from "./api/LoadTestPanel";
import { ApiSuiteScenarioPicker } from "./api/ApiSuiteScenarioPicker";
import { JmxImportPanel } from "./api/JmxImportPanel";
import { ApiPostmanWorkspace, type PostmanPane } from "./api/ApiPostmanWorkspace";
import { ApiCollapsibleSection, ApiSection, API_INPUT_CLASS, apiBtnClass, apiInputStyle } from "./api/apiUi";
import { EliaButton } from "../components/ui";
import { analyzeFlowNodeCounts, deserializeFlowNodes } from "./api/FlowControllerEditor";
import {
  loadApiSurfacePersistProject,
  useApiSurfacePersist,
  type ApiSurfacePersistedFields,
} from "./api/useApiSurfacePersist";
import {
  canExecuteHomeActions,
  getFeatureAccess,
  shouldShowTierUpsell,
  type EntitlementPhase,
} from "../app/entitlementPhase";
import type { LicenseState } from "../app/licenseUtils";
import { FeatureGate } from "../components/FeatureGate";
import { LoadingStatusRow } from "../components/LoadingStatusRow";
import { ProjectManageToolbar } from "../components/ProjectManageToolbar";
import { ProjectTemplateModal } from "../components/ProjectTemplateModal";
import { PlatformQuickGuide } from "../components/PlatformQuickGuide";
import { UpsellModal } from "../components/UpsellModal";
import { useHomeUiContext } from "../context/HomeUiContext";
import type { FeatureFlags, ModulesStatus } from "../types";

type Props = {
  c: Record<string, string>;
  modules: ModulesStatus | null;
  modulesLoading?: boolean;
  canRunJobs: boolean;
  entitlementPhase: EntitlementPhase;
  entitlementFeatures: FeatureFlags;
  showTierUpsell: boolean;
  license: LicenseState | null;
  onShowError: (msg: string) => void;
  setHomeHint: (msg: string | null) => void;
};

type HeaderRow = { key: string; value: string };
type ExecResult = Awaited<ReturnType<typeof executeApiRequest>>;
type ApiSubTab = "postman" | "load";

const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"];

function pickPreferredApiCollection(cols: ApiCollectionRow[], list: ApiScenarioRow[]): string {
  if (!cols.length) return "_default";
  const withCount = cols.filter((col) => col.scenario_count > 0);
  const idsWithScenarios = new Set(list.map((s) => s.collection_id));
  const nonEmpty = withCount.length ? withCount : cols.filter((col) => idsWithScenarios.has(col.id));
  const preferred = nonEmpty.find((col) => col.id !== "_default") ?? nonEmpty[0] ?? cols[0];
  return preferred?.id ?? "_default";
}

export function ApiSurface(props: Props) {
  const {
    c,
    modules,
    modulesLoading,
    canRunJobs,
    entitlementPhase,
    entitlementFeatures,
    showTierUpsell,
    license,
    onShowError,
    setHomeHint,
  } = props;
  const [projects, setProjects] = useState<string[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [project, setProject] = useState(() => loadApiSurfacePersistProject() || "DefaultApi");
  const [newProject, setNewProject] = useState("");
  const [scenarios, setScenarios] = useState<ApiScenarioRow[]>([]);
  const [scenariosLoading, setScenariosLoading] = useState(false);
  const [collections, setCollections] = useState<ApiCollectionRow[]>([]);
  const [activeCollectionId, setActiveCollectionId] = useState("_default");
  const [captures, setCaptures] = useState<{ id: string; name: string; path: string }[]>([]);
  const [environments, setEnvironments] = useState<string[]>(["dev"]);
  const [environment, setEnvironment] = useState("dev");
  const [envVarsText, setEnvVarsText] = useState('{\n  "base_url": "https://api.ejemplo.com"\n}');
  const [globalHeaders, setGlobalHeaders] = useState<HeaderRow[]>([{ key: "", value: "" }]);
  const [method, setMethod] = useState("GET");
  const [url, setUrl] = useState("{{base_url}}/recurso");
  const [body, setBody] = useState("");
  const [expectedStatus, setExpectedStatus] = useState("200");
  const [reqHeaders, setReqHeaders] = useState<HeaderRow[]>([{ key: "Content-Type", value: "application/json" }]);
  const [selectedScenarios, setSelectedScenarios] = useState<Record<string, boolean>>({});
  const [loadUsers, setLoadUsers] = useState("5");
  const [loadSpawn, setLoadSpawn] = useState("1");
  const [loadRunTime, setLoadRunTime] = useState("1m");
  const [loadHost, setLoadHost] = useState("");
  const [scenarioWeights, setScenarioWeights] = useState<Record<string, string>>({});
  const [assertions, setAssertions] = useState<AssertionRow[]>([]);
  const [extractors, setExtractors] = useState<ExtractorRow[]>([]);
  const [maxDurationMs, setMaxDurationMs] = useState("");
  const [requestWeight, setRequestWeight] = useState("1");
  const [generateLoadReport, setGenerateLoadReport] = useState(false);
  const [loadRunFinished, setLoadRunFinished] = useState(false);
  const [loadReportFilename, setLoadReportFilename] = useState<string | null>(null);
  const [loadFlowId, setLoadFlowId] = useState("");
  const [loadFlowCounts, setLoadFlowCounts] = useState<Record<string, number>>({});
  const [runSetupFlow, setRunSetupFlow] = useState(false);
  const [savedLoadFlows, setSavedLoadFlows] = useState<{ id: string; name: string }[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [execResult, setExecResult] = useState<ExecResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);
  const [loadedScenarioMeta, setLoadedScenarioMeta] = useState<{ id: string; source: string } | null>(null);
  const [scenarioName, setScenarioName] = useState("");
  const [preRequestScript, setPreRequestScript] = useState("");
  const [postRequestScript, setPostRequestScript] = useState("");
  const initialized = useRef(false);
  const pendingAutoLoadRef = useRef(false);
  const [importKind, setImportKind] = useState<"postman" | "openapi">("postman");
  const [apiTab, setApiTab] = useState<ApiSubTab>("postman");
  const [postmanPane, setPostmanPane] = useState<PostmanPane>("request");
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [loadSettings, setLoadSettings] = useState<LoadTestSettings>(defaultLoadTestSettings);
  const [jmxImportMeta, setJmxImportMeta] = useState<JmxImportMeta | null>(null);
  const [webOriginAvailable, setWebOriginAvailable] = useState(false);
  const [upsell, setUpsell] = useState<null | "api_postman" | "api_locust">(null);
  const [confirm, setConfirm] = useState<null | {
    title: string;
    message: string;
    destructive?: boolean;
    onConfirm: () => void;
  }>(null);
  const [preflightBusy, setPreflightBusy] = useState(false);
  const [suiteHistoryRefresh, setSuiteHistoryRefresh] = useState(0);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const { refreshHomeData, pendingApiProject, clearPendingApiProject, homeDataRefresh } = useHomeUiContext();
  const features = entitlementFeatures;
  const actionsEnabled = canExecuteHomeActions(entitlementPhase, canRunJobs);
  const postmanAccess = getFeatureAccess(entitlementPhase, "api_postman_suites", features, license);
  const locustAccess = getFeatureAccess(entitlementPhase, "api_locust", features, license);
  const showPostmanUpsell = shouldShowTierUpsell(entitlementPhase, postmanAccess, showTierUpsell);

  const upsellButton = (tier: "api_postman" | "api_locust", message: string) => (
    <EliaButton variant="ghost" onClick={() => setUpsell(tier)}>
      🔒 {message}
    </EliaButton>
  );

  const envVarNames = useMemo(() => {
    try {
      const parsed = JSON.parse(envVarsText) as unknown;
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return Object.keys(parsed as Record<string, unknown>);
      }
    } catch {
      /* ignore invalid JSON while typing */
    }
    return [];
  }, [envVarsText]);

  const handlePersistRestore = useCallback((fields: ApiSurfacePersistedFields) => {
    setUrl(fields.url);
    setPreRequestScript(fields.preRequestScript);
    setPostRequestScript(fields.postRequestScript);
    setApiTab(fields.apiTab);
  }, []);

  useApiSurfacePersist(
    project,
    { url, preRequestScript, postRequestScript, apiTab },
    handlePersistRestore,
  );


  const refreshProjects = useCallback(() => {
    setProjectsLoading(true);
    void getApiProjects()
      .then((r) => setProjects(r.projects))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setProjectsLoading(false));
  }, [onShowError]);

  const applyScenarioDetail = useCallback((scenarioId: string, s: Record<string, unknown>) => {
    setActiveScenarioId(scenarioId);
    const colId = scenarioId.includes("/") ? scenarioId.split("/")[0] : "_default";
    setActiveCollectionId(colId);
    setLoadedScenarioMeta({ id: String(s.id || scenarioId.replace(/\.json$/i, "")), source: String(s.source || "manual") });
    setScenarioName(String(s.name || ""));
    setMethod(String(s.method || "GET"));
    setUrl(String(s.url || ""));
    setBody(String(s.body || ""));
    setExpectedStatus(String(s.expected_status || 200));
    const hdrs = Object.entries((s.headers as Record<string, string>) || {}).map(([key, value]) => ({
      key,
      value,
    }));
    setReqHeaders(hdrs.length ? hdrs : [{ key: "", value: "" }]);
    const rawAssertions = (s.assertions as Array<{ kind: string; expression?: string; expected?: string }>) || [];
    setAssertions(
      rawAssertions.length
        ? rawAssertions.map((a) => ({ kind: a.kind, expression: a.expression || "", expected: a.expected || "" }))
        : [],
    );
    const rawExtractors = (s.extractors as Array<{ kind: string; expression?: string; target_var?: string }>) || [];
    setExtractors(
      rawExtractors.length
        ? rawExtractors.map((e) => ({ kind: e.kind, expression: e.expression || "", target_var: e.target_var || "" }))
        : [],
    );
    setMaxDurationMs(s.max_duration_ms != null ? String(s.max_duration_ms) : "");
    setRequestWeight(String(s.weight || 1));
    setPreRequestScript(String(s.pre_request_script || ""));
    setPostRequestScript(String(s.post_request_script || ""));
    setApiTab("postman");
    setPostmanPane("request");
  }, []);

  const loadScenarioIntoWorkspace = useCallback(
    (scenarioId: string) => {
      if (!project.trim()) return;
      setBusy(true);
      void getApiScenarioDetail(project, scenarioId)
        .then((r) => applyScenarioDetail(scenarioId, r.scenario as Record<string, unknown>))
        .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
        .finally(() => setBusy(false));
    },
    [project, applyScenarioDetail, onShowError],
  );

  const refreshScenarios = useCallback(
    (opts?: { autoLoadFirst?: boolean }) => {
      if (!project.trim()) return;
      setScenariosLoading(true);
      void getApiScenarios(project)
        .then((r) => {
          const cols = (r.collections || []).map((col) => ({
            id: col.id,
            name: col.name,
            scenario_count: col.scenario_count,
          }));
          setCollections(cols);
          const list: ApiScenarioRow[] = r.scenarios.map((s) => ({
            id: s.id,
            name: s.name,
            collection_id: s.collection_id,
            collection_name: s.collection_name,
          }));
          setScenarios(list);
          setSelectedScenarios((prev) => {
            const next: Record<string, boolean> = {};
            for (const s of list) next[s.id] = prev[s.id] ?? true;
            return next;
          });
          const preferredCol = pickPreferredApiCollection(cols, list);
          setActiveCollectionId(preferredCol);
          const shouldAutoLoad = (opts?.autoLoadFirst || pendingAutoLoadRef.current) && list.length > 0;
          if (shouldAutoLoad) {
            pendingAutoLoadRef.current = false;
            const target = list.find((s) => s.collection_id === preferredCol) ?? list[0];
            loadScenarioIntoWorkspace(target.id);
          }
        })
        .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
        .finally(() => setScenariosLoading(false));
    },
    [project, onShowError, loadScenarioIntoWorkspace],
  );

  const applyJmxLoadSuggestion = useCallback((suggestion: Record<string, unknown>, csvBasename?: string | null) => {
    if (suggestion.users != null) setLoadUsers(String(suggestion.users));
    if (suggestion.spawn_rate != null) setLoadSpawn(String(suggestion.spawn_rate));
    if (suggestion.run_time != null) setLoadRunTime(String(suggestion.run_time));
    setLoadSettings((prev) => ({
      ...prev,
      ...(suggestion.profile ? { profile: String(suggestion.profile) } : {}),
      ...(csvBasename ? { dataFile: csvBasename } : {}),
    }));
  }, []);

  const refreshJmxImportState = useCallback(() => {
    if (!project.trim()) {
      setJmxImportMeta(null);
      return;
    }
    void getJmxImportMeta(project)
      .then((r) => {
        setJmxImportMeta(r.meta);
        if (!r.meta) {
          setLoadFlowId((prev) => {
            if (prev && prev.startsWith("Suite .jmx")) return "";
            return prev;
          });
        }
      })
      .catch(() => setJmxImportMeta(null));
    void listApiFlows(project)
      .then((r) => {
        const flows = r.flows.map((f) => ({ id: f.id, name: f.name }));
        setSavedLoadFlows(flows);
        setLoadFlowId((prev) => (prev && !flows.some((f) => f.id === prev) ? "" : prev));
      })
      .catch(() => setSavedLoadFlows([]));
  }, [project]);

  const handleJmxImported = useCallback(
    (result: JmxImportResult) => {
      refreshScenarios();
      void listApiFlows(project)
        .then((r) => {
          setSavedLoadFlows(r.flows.map((f) => ({ id: f.id, name: f.name })));
          if (result.flow_id) setLoadFlowId(result.flow_id);
        })
        .catch(() => setSavedLoadFlows([]));
      if (result.scenario_ids?.length) {
        setSelectedScenarios((prev) => {
          const next = { ...prev };
          for (const id of result.scenario_ids) next[id] = true;
          return next;
        });
      }
      if (result.load_suggestion) {
        applyJmxLoadSuggestion(result.load_suggestion, result.csv_basename);
      }
      setJmxImportMeta({
        source_file: result.report.source_file,
        flow_id: result.flow_id,
        flow_name: result.flow_name,
        load_suggestion: result.load_suggestion,
        csv_basename: result.csv_basename,
        scenario_ids: result.scenario_ids,
      });
      setHomeHint(
        `Importación .jmx: ${result.count} escenarios, flujo «${result.flow_name}» y parámetros Locust aplicados.`,
      );
    },
    [project, refreshScenarios, applyJmxLoadSuggestion, setHomeHint],
  );

  const refreshCaptures = () => {
    if (!project.trim()) return;
    void getApiTrafficCaptures(project)
      .then((r) => setCaptures(r.captures))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  const refreshConfig = () => {
    if (!project.trim()) return;
    void getApiProjectConfig(project)
      .then((cfg) => {
        setEnvironment(cfg.default_environment || "dev");
        const rows = Object.entries(cfg.global_headers || {}).map(([key, value]) => ({ key, value }));
        setGlobalHeaders(rows.length ? rows : [{ key: "", value: "" }]);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
    void getApiEnvironments(project)
      .then((r) => setEnvironments(r.environments.length ? r.environments : ["dev"]))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  const loadEnvironmentVars = (envName: string) => {
    void getApiEnvironment(project, envName)
      .then((env) => {
        setEnvVarsText(JSON.stringify(env.variables || {}, null, 2));
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  };

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
    }
    refreshProjects();
  }, [homeDataRefresh, refreshProjects]);

  useEffect(() => {
    refreshScenarios();
    refreshCaptures();
    refreshConfig();
    setActiveCollectionId("_default");
    setActiveScenarioId(null);
    setLoadedScenarioMeta(null);
    setScenarioName("");
    setPreRequestScript("");
    setPostRequestScript("");
    setExecResult(null);
  }, [project]);

  useEffect(() => {
    if (!pendingApiProject?.trim()) return;
    refreshProjects();
    setProject(pendingApiProject);
    pendingAutoLoadRef.current = true;
    clearPendingApiProject();
  }, [pendingApiProject, clearPendingApiProject]);

  useEffect(() => {
    if (project && environment) loadEnvironmentVars(environment);
    void getApiWebOrigin(project)
      .then((r) => setWebOriginAvailable(r.available))
      .catch(() => setWebOriginAvailable(false));
  }, [project, environment]);

  useEffect(() => {
    if (!project.trim()) return;
    void listApiFlows(project)
      .then((r) => setSavedLoadFlows(r.flows.map((f) => ({ id: f.id, name: f.name }))))
      .catch(() => setSavedLoadFlows([]));
    setLoadFlowId("");
    setLoadFlowCounts({});
    setRunSetupFlow(false);
  }, [project]);

  useEffect(() => {
    if (!project.trim()) {
      setJmxImportMeta(null);
      return;
    }
    refreshJmxImportState();
  }, [project, refreshJmxImportState]);

  useEffect(() => {
    if (!project.trim() || !loadFlowId) {
      setLoadFlowCounts({});
      setRunSetupFlow(false);
      return;
    }
    void getApiFlow(project, loadFlowId)
      .then((r) => {
        const flow = r.flow as Record<string, unknown>;
        const nodes = deserializeFlowNodes((flow.nodes as Record<string, unknown>[]) ?? []);
        const counts = analyzeFlowNodeCounts(nodes);
        setLoadFlowCounts(counts);
        setRunSetupFlow((counts.sql ?? 0) > 0);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)));
  }, [project, loadFlowId]);

  useEffect(() => {
    if (!runId) {
      setLoadRunFinished(false);
      return;
    }
    let cancelled = false;
    const poll = () => {
      void getTestRun(runId).then((run) => {
        if (cancelled) return;
        if (run.state === "done" || run.state === "error") {
          setLoadRunFinished(true);
          return;
        }
        window.setTimeout(poll, 1200);
      });
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    if (!runId || !loadRunFinished) return;
    const ids = scenarios.filter((s) => selectedScenarios[s.id]).map((s) => s.id);
    void saveApiLoadSnapshot({
      project,
      run_id: runId,
      users: Number(loadUsers) || 5,
      run_time: loadRunTime.trim() || "1m",
      host: loadHost.trim(),
      scenario_count: ids.length,
      profile: loadSettings.profile,
      sla: buildSlaPayload(loadSettings),
    })
      .then(() => setHistoryRefresh((n) => n + 1))
      .catch(() => undefined);
  }, [loadRunFinished, runId]);

  const httpAccess = getFeatureAccess(entitlementPhase, "api_http_single", features, license);

  if (httpAccess === "pending") {
    return (
      <LoadingStatusRow
        c={c}
        text="Cargando módulo API…"
        loading
        testId="elia-api-http-pending"
      />
    );
  }

  if (httpAccess === "denied") {
    return (
      <div style={{ fontSize: 14, color: c.muted }}>
        El módulo de pruebas API requiere licencia vigente con acceso HTTP habilitado.
      </div>
    );
  }

  const headersToRecord = (rows: HeaderRow[]) =>
    Object.fromEntries(rows.filter((r) => r.key.trim()).map((r) => [r.key.trim(), r.value]));

  const buildRequestPayload = () => ({
    id: loadedScenarioMeta?.id || `manual-${Date.now()}`,
    name: scenarioName.trim() || `${method} ${url.split("?")[0].slice(-40)}`,
    method,
    url: url.trim(),
    body: body.trim() || null,
    expected_status: Number(expectedStatus) || 200,
    headers: headersToRecord(reqHeaders),
    assertions: assertions.filter((a) => a.kind).map((a) => ({ kind: a.kind, expression: a.expression, expected: a.expected })),
    extractors: extractors.filter((e) => e.target_var.trim()).map((e) => ({ kind: e.kind, expression: e.expression, target_var: e.target_var })),
    max_duration_ms: maxDurationMs.trim() ? Number(maxDurationMs) : null,
    weight: Number(requestWeight) || 1,
    source: loadedScenarioMeta?.source || "manual",
    pre_request_script: preRequestScript.trim() || null,
    post_request_script: postRequestScript.trim() || null,
  });

  const handleSend = () => {
    if (!url.trim()) {
      onShowError("URL requerida.");
      return;
    }
    setBusy(true);
    setExecResult(null);
    void executeApiRequest({ project, environment, request: buildRequestPayload() })
      .then((r) => {
        setExecResult(r);
        if (r.variables && typeof r.variables === "object") {
          setEnvVarsText(JSON.stringify(r.variables, null, 2));
        }
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleSaveScenario = () => {
    if (!url.trim()) {
      onShowError("URL requerida para guardar escenario API.");
      return;
    }
    setBusy(true);
    void saveApiScenario({
      project,
      scenario: buildRequestPayload(),
      scenario_id: activeScenarioId || undefined,
      collection_id: activeScenarioId ? undefined : activeCollectionId,
    })
      .then((r) => {
        refreshScenarios();
        if (r.scenario_id) {
          setActiveScenarioId(r.scenario_id);
        }
        setHomeHint("Escenario API guardado.");
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleSaveGlobalConfig = () => {
    setBusy(true);
    void saveApiProjectConfig(project, {
      default_environment: environment,
      global_headers: headersToRecord(globalHeaders),
    })
      .then(() => setHomeHint("Configuración del proyecto guardada."))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleSaveEnvironment = () => {
    let variables: Record<string, string>;
    try {
      const parsed = JSON.parse(envVarsText);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        throw new Error("El entorno debe ser un objeto JSON");
      }
      variables = Object.fromEntries(Object.entries(parsed).map(([k, v]) => [k, String(v)]));
    } catch (e: unknown) {
      onShowError(`Variables de entorno inválidas: ${String((e as Error)?.message ?? e)}`);
      return;
    }
    setBusy(true);
    void saveApiEnvironment(project, environment, { name: environment, variables })
      .then(() => setHomeHint(`Entorno ${environment} guardado.`))
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleImportCapture = (captureId: string) => {
    setBusy(true);
    void importApiTrafficCapture(project, captureId)
      .then((r) => {
        refreshScenarios();
        const skipped = r.skipped ? ` (${r.skipped} duplicados omitidos)` : "";
        setHomeHint(`${r.imported ?? r.count} escenario(s) importado(s)${skipped}.`);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleSyncFromWeb = () => {
    setBusy(true);
    void syncApiEnvironmentFromWeb(project, environment)
      .then((r) => {
        loadEnvironmentVars(environment);
        setHomeHint(`base_url sincronizado desde web: ${r.base_url}`);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleLoadScenario = (scenarioId: string) => {
    loadScenarioIntoWorkspace(scenarioId);
  };

  const handleRenameScenario = (scenarioId: string, newName: string) => {
    setBusy(true);
    void getApiScenarioDetail(project, scenarioId)
      .then((r) =>
        saveApiScenario({
          project,
          scenario: { ...(r.scenario as Record<string, unknown>), name: newName },
          scenario_id: scenarioId,
        }),
      )
      .then(() => {
        if (activeScenarioId === scenarioId) setScenarioName(newName);
        refreshScenarios();
        setHomeHint("Escenario renombrado.");
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleDeleteSelectedScenarios = (scenarioIds: string[]) => {
    if (!scenarioIds.length) return;
    setConfirm({
      title: "Eliminar escenarios seleccionados",
      message: `¿Eliminar ${scenarioIds.length} escenario(s) seleccionado(s)? Esta acción no se puede deshacer.`,
      destructive: true,
      onConfirm: () => {
        setConfirm(null);
        setBusy(true);
        void deleteApiScenarios({ project, scenario_ids: scenarioIds })
          .then(() => {
            if (activeScenarioId && scenarioIds.includes(activeScenarioId)) {
              setActiveScenarioId(null);
              setLoadedScenarioMeta(null);
            }
            setSelectedScenarios((prev) => {
              const next = { ...prev };
              for (const id of scenarioIds) delete next[id];
              return next;
            });
            refreshScenarios();
            refreshJmxImportState();
            setHomeHint(`${scenarioIds.length} escenario(s) eliminado(s).`);
          })
          .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
          .finally(() => setBusy(false));
      },
    });
  };

  const handleDeleteScenario = (scenarioId: string) => {
    const name = scenarios.find((s) => s.id === scenarioId)?.name || scenarioId;
    setConfirm({
      title: "Eliminar escenario",
      message: `¿Eliminar el escenario "${name}"?`,
      destructive: true,
      onConfirm: () => {
        setConfirm(null);
        setBusy(true);
        void deleteApiScenario(project, scenarioId)
          .then(() => {
            if (activeScenarioId === scenarioId) {
              setActiveScenarioId(null);
              setLoadedScenarioMeta(null);
            }
            setSelectedScenarios((prev) => {
              const next = { ...prev };
              delete next[scenarioId];
              return next;
            });
            refreshScenarios();
            refreshJmxImportState();
            setHomeHint("Escenario eliminado.");
          })
          .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
          .finally(() => setBusy(false));
      },
    });
  };

  const handleDeleteCollection = (collectionId: string) => {
    const col = collections.find((c) => c.id === collectionId);
    const label = col?.name || collectionId;
    const count = scenarios.filter((s) => s.collection_id === collectionId).length;
    const isDefault = collectionId === "_default";
    const confirmMsg = isDefault
      ? `¿Vaciar la colección "${label}"? Se eliminarán sus ${count} escenario(s). La colección General permanecerá vacía.`
      : `¿Eliminar la colección "${label}" y sus ${count} escenario(s)? Esta acción no se puede deshacer.`;
    setConfirm({
      title: isDefault ? "Vaciar colección" : "Eliminar colección",
      message: confirmMsg,
      destructive: true,
      onConfirm: () => {
        setConfirm(null);
        setBusy(true);
        void deleteApiCollection(project, collectionId)
          .then((r) => {
            if (activeScenarioId?.startsWith(`${collectionId}/`)) {
              setActiveScenarioId(null);
              setLoadedScenarioMeta(null);
              setScenarioName("");
            }
            setSelectedScenarios((prev) => {
              const next = { ...prev };
              for (const s of scenarios) {
                if (s.collection_id === collectionId) delete next[s.id];
              }
              return next;
            });
            if (!isDefault && activeCollectionId === collectionId) {
              setActiveCollectionId("_default");
            }
            refreshScenarios();
            refreshJmxImportState();
            setHomeHint(
              isDefault
                ? `Colección "${label}" vaciada (${r.deleted_scenarios} escenario(s) eliminados).`
                : `Colección eliminada (${r.deleted_scenarios} escenario(s)).`,
            );
          })
          .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
          .finally(() => setBusy(false));
      },
    });
  };

  const handleCloneScenario = (scenarioId: string) => {
    setBusy(true);
    void cloneApiScenario(project, scenarioId)
      .then((r) => {
        refreshScenarios();
        if (r.scenario_id) {
          handleLoadScenario(r.scenario_id);
        }
        setHomeHint("Escenario duplicado.");
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleLoadPreflight = () => {
    setPreflightBusy(true);
    void loadPreflightApi({
      mode: loadSettings.mode === "standalone" ? "local" : loadSettings.mode,
      master_host: loadSettings.masterHost.trim() || "127.0.0.1",
      master_port: Number(loadSettings.masterPort) || 5557,
    })
      .then((r) => {
        const failed = r.checks.filter((c) => !c.ok);
        if (r.ok) {
          setHomeHint("Preflight de carga: todas las comprobaciones OK.");
        } else {
          onShowError(failed.map((c) => c.message).join(" · ") || "Preflight de carga falló.");
        }
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setPreflightBusy(false));
  };

  const handleImportFile = (file: File) => {
    setBusy(true);
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result || "{}"));
        const task =
          importKind === "postman"
            ? importPostmanCollection({ project, collection: parsed })
            : importOpenApiSpec({ project, spec: parsed });
        void task
          .then((r) => {
            refreshScenarios();
            if (environment) loadEnvironmentVars(environment);
            const varsMsg = "variables_imported" in r && r.variables_imported ? ` (${r.variables_imported} variables de colección)` : "";
            const colMsg = r.collection_name ? ` en colección «${r.collection_name}»` : "";
            if (r.collection_id) setActiveCollectionId(r.collection_id);
            setHomeHint(`${r.count} escenario(s) importado(s)${colMsg}${varsMsg}.`);
          })
          .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
          .finally(() => setBusy(false));
      } catch (e: unknown) {
        setBusy(false);
        onShowError(`JSON inválido: ${String((e as Error)?.message ?? e)}`);
      }
    };
    reader.readAsText(file);
  };

  const handleExportEvidence = (format: "pdf" | "json") => {
    if (!execResult) return;
    setBusy(true);
    void exportApiRequestEvidence({
      project,
      environment,
      request: buildRequestPayload(),
      result: execResult,
      format,
    })
      .then((r) => {
        if (format === "pdf") {
          window.open(getProjectReportUrl("api", project, r.filename), "_blank");
          setHomeHint(`Evidencia PDF guardada: ${r.filename}`);
        } else {
          window.open(getProjectEvidenceUrl("api", project, r.filename), "_blank");
          void openProjectFolder("api", project, "outputs/evidences").catch(() => undefined);
          setHomeHint(`Evidencia JSON guardada y abierta: ${r.filename}`);
        }
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleExportLoadReport = (format: "pdf" | "html" = "pdf") => {
    if (!runId) return;
    const ids = scenarios.filter((s) => selectedScenarios[s.id]).map((s) => s.id);
    setBusy(true);
    void exportApiLoadEvidence({
      project,
      run_id: runId,
      users: Number(loadUsers) || 5,
      run_time: loadRunTime.trim() || "1m",
      host: loadHost.trim(),
      scenario_count: ids.length,
      format,
      enriched: true,
    })
      .then((r) => {
        setLoadReportFilename(r.filename);
        window.open(getProjectReportUrl("api", project, r.filename), "_blank");
        setHomeHint(`Reporte de carga (${format.toUpperCase()}) generado: ${r.filename}`);
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  const handleRunLocust = () => {
    const ids = scenarios.filter((s) => selectedScenarios[s.id]).map((s) => s.id);
    if (!loadFlowId && !ids.length) {
      onShowError("Selecciona escenarios o un flujo guardado para Locust.");
      return;
    }
    const distErr = validateDistributedLoadSettings(loadSettings);
    if (distErr) {
      onShowError(distErr);
      return;
    }
    setBusy(true);
    setLoadRunFinished(false);
    setLoadReportFilename(null);
    void runLoadTest({
      project,
      users: Number(loadUsers) || 5,
      spawn_rate: Number(loadSpawn) || 1,
      run_time: loadRunTime.trim() || "1m",
      host: loadHost.trim(),
      scenario_ids: ids.length ? ids : undefined,
      scenario_weights: ids.length
        ? Object.fromEntries(ids.map((id) => [id, Number(scenarioWeights[id]) || 1]))
        : undefined,
      collect_metrics: true,
      flow_id: loadFlowId || undefined,
      run_setup_flow: runSetupFlow && !!loadFlowId,
      environment,
      profile: loadSettings.profile,
      think_time: buildThinkTimePayload(loadSettings),
      sla: buildSlaPayload(loadSettings),
      data_file: loadSettings.dataFile || undefined,
      processes: Number(loadSettings.processes) || 0,
      mode: loadSettings.mode,
      master_host: loadSettings.mode !== "standalone" ? loadSettings.masterHost : undefined,
      master_port:
        loadSettings.mode !== "standalone" ? Number(loadSettings.masterPort) || undefined : undefined,
      expect_workers: loadSettings.mode === "master" ? Number(loadSettings.expectWorkers) || undefined : undefined,
    })
      .then((r) => {
        setRunId(r.run_id);
        if (r.flow_node_counts) {
          setLoadFlowCounts(r.flow_node_counts);
        }
        if (r.setup_sql) {
          setHomeHint("Pre-carga SQL ejecutada; variables inyectadas en Locust.");
        }
        if (loadSettings.mode === "worker") {
          setHomeHint("Worker Locust iniciado; conectando al master…");
        } else if (loadSettings.mode === "master") {
          setHomeHint("Master Locust iniciado; lanza workers en otras máquinas con el mismo proyecto.");
        }
      })
      .catch((e: unknown) => onShowError(String((e as Error)?.message ?? e)))
      .finally(() => setBusy(false));
  };

  return (
    <div data-testid="elia-api-panel" className="elia-panel elia-hud-panel elia-panel--padded">
      {upsell ? <UpsellModal c={c} requiredTier={upsell} onClose={() => setUpsell(null)} /> : null}
      {confirm ? (
        <ConfirmModal
          c={c}
          title={confirm.title}
          message={confirm.message}
          destructive={confirm.destructive}
          confirmLabel={confirm.destructive ? "Eliminar" : "Confirmar"}
          onConfirm={confirm.onConfirm}
          onCancel={() => setConfirm(null)}
        />
      ) : null}
      <div style={{ fontSize: 14, marginBottom: 12, color: c.text }}>
        Pruebas API: cliente de peticiones, suites encadenadas y pruebas de carga (motor Locust).
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14, alignItems: "center" }}>
        <label style={{ fontSize: 13, color: c.muted }}>Proyecto</label>
        <select
          value={project}
          disabled={projectsLoading}
          onChange={(e) => setProject(e.target.value)}
          className={API_INPUT_CLASS}
          style={apiInputStyle(c, { minWidth: 140, opacity: projectsLoading ? 0.7 : 1 })}
          data-testid="elia-api-project-select"
        >
          {projectsLoading ? (
            <option value={project}>Cargando proyectos…</option>
          ) : (
            [...new Set([project, ...projects])].map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))
          )}
        </select>
        {projectsLoading ? (
          <LoadingStatusRow
            c={c}
            text="Cargando proyectos…"
            loading
            testId="elia-api-projects-loading"
          />
        ) : null}
        <input
          value={newProject}
          onChange={(e) => setNewProject(e.target.value)}
          placeholder="Nuevo proyecto"
          className={API_INPUT_CLASS}
          style={apiInputStyle(c, { minWidth: 160 })}
        />
        <button
          type="button"
          disabled={!newProject.trim() || busy}
          className={apiBtnClass()}
          onClick={() => {
            void createApiProject(newProject.trim()).then(() => {
              setProject(newProject.trim());
              setNewProject("");
              refreshProjects();
            });
          }}
        >
          Crear
        </button>
        <button
          type="button"
          data-testid="elia-api-new-from-template-btn"
          disabled={busy || !actionsEnabled}
          className={apiBtnClass(false, true)}
          onClick={() => setTemplateModalOpen(true)}
        >
          Desde plantilla…
        </button>
        <label style={{ fontSize: 13, color: c.muted }}>Entorno</label>
        <select
          value={environment}
          onChange={(e) => setEnvironment(e.target.value)}
          className={API_INPUT_CLASS}
          style={apiInputStyle(c, { minWidth: 100 })}
        >
          {environments.map((env) => (
            <option key={env} value={env}>
              {env}
            </option>
          ))}
        </select>
      </div>

      {project.trim() ? (
        <ProjectManageToolbar
          c={c}
          platform="api"
          project={project}
          disabled={!actionsEnabled || busy}
          onProjectRenamed={(newName) => {
            refreshHomeData();
            refreshProjects();
            setProject(newName);
          }}
          onProjectDeleted={() => {
            refreshHomeData();
            refreshProjects();
            setProject("");
          }}
          onError={onShowError}
        />
      ) : null}

      <div className="elia-tab-bar" style={{ marginBottom: 16 }}>
        {(
          [
            { id: "postman" as const, label: "Cliente API" },
            { id: "load" as const, label: "Suites y carga" },
          ] as const
        ).map(({ id, label }) => (
          <button
            key={id}
            type="button"
            data-testid={`elia-api-subtab-${id}`}
            onClick={() => setApiTab(id)}
            className={`elia-btn elia-btn--tab${apiTab === id ? " is-active" : ""}`}
          >
            {label}
          </button>
        ))}
      </div>

      {apiTab === "postman" ? (
        <div
          data-testid="elia-api-postman-layout"
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(220px, 28%) 1fr",
            gap: 14,
            alignItems: "start",
          }}
        >
          <FeatureGate
            c={c}
            phase={entitlementPhase}
            feature="api_postman_suites"
            features={features}
            license={license}
            showTierUpsell={showTierUpsell}
            minHeight="min(62vh, 640px)"
            upsellOverlay={upsellButton(
              "api_postman",
              "Desbloquea la importación de colecciones con ELIA Tester",
            )}
          >
            <ApiPostmanSidebar
              c={c}
              busy={busy}
              canRunJobs={actionsEnabled}
              scenariosLoading={scenariosLoading}
              collections={collections}
              scenarios={scenarios}
              activeScenarioId={activeScenarioId}
              activeCollectionId={activeCollectionId}
              onActiveCollectionChange={setActiveCollectionId}
              captures={captures}
              importKind={importKind}
              onImportKindChange={setImportKind}
              onImportFile={handleImportFile}
              onImportCapture={handleImportCapture}
              onLoadScenario={handleLoadScenario}
              onRenameScenario={handleRenameScenario}
              onDeleteScenario={handleDeleteScenario}
              onDeleteCollection={handleDeleteCollection}
              onCloneScenario={postmanAccess === "granted" ? handleCloneScenario : undefined}
              webOriginAvailable={webOriginAvailable}
              onSyncFromWeb={handleSyncFromWeb}
            />
          </FeatureGate>
          <ApiPostmanWorkspace
            c={c}
            busy={busy}
            canRunJobs={actionsEnabled}
            pane={postmanPane}
            onPaneChange={setPostmanPane}
            envVarsText={envVarsText}
            onEnvVarsTextChange={setEnvVarsText}
            globalHeaders={globalHeaders}
            onGlobalHeadersChange={setGlobalHeaders}
            webOriginAvailable={webOriginAvailable}
            onSaveEnvironment={handleSaveEnvironment}
            onSaveGlobalConfig={handleSaveGlobalConfig}
            onSyncFromWeb={handleSyncFromWeb}
            scenarioName={scenarioName}
            onScenarioNameChange={setScenarioName}
            activeScenarioId={activeScenarioId}
            method={method}
            methods={METHODS}
            onMethodChange={setMethod}
            url={url}
            onUrlChange={setUrl}
            expectedStatus={expectedStatus}
            onExpectedStatusChange={setExpectedStatus}
            reqHeaders={reqHeaders}
            onReqHeadersChange={setReqHeaders}
            maxDurationMs={maxDurationMs}
            onMaxDurationMsChange={setMaxDurationMs}
            assertions={assertions}
            onAssertionsChange={setAssertions}
            extractors={extractors}
            onExtractorsChange={setExtractors}
            body={body}
            onBodyChange={setBody}
            onSend={handleSend}
            onSaveScenario={
              postmanAccess === "granted"
                ? handleSaveScenario
                : () => {
                    if (showPostmanUpsell) setUpsell("api_postman");
                  }
            }
            preRequestScript={preRequestScript}
            onPreRequestScriptChange={setPreRequestScript}
            postRequestScript={postRequestScript}
            onPostRequestScriptChange={setPostRequestScript}
            execResult={execResult}
            onExportEvidence={handleExportEvidence}
          />
        </div>
      ) : (
        <>
          <PlatformQuickGuide
            c={c}
            platform="api_load"
            showLink
            showRunnerHint
          />
          <FeatureGate
            c={c}
            phase={entitlementPhase}
            feature="api_postman_suites"
            features={features}
            license={license}
            showTierUpsell={showTierUpsell}
            upsellOverlay={upsellButton("api_postman", "Desbloquea suites funcionales con ELIA Tester")}
          >
            <>
              <ApiSection c={c} title="Migración .jmx">
                <JmxImportPanel
                  c={c}
                  project={project}
                  busy={busy}
                  onError={onShowError}
                  onHint={setHomeHint}
                  onImported={handleJmxImported}
                />
              </ApiSection>

              <ApiSection c={c} title="Datos CSV (data-driven)">
                <DataCsvPanel c={c} project={project} busy={busy} onError={onShowError} onHint={setHomeHint} />
              </ApiSection>

              <ApiCollapsibleSection
                c={c}
                title={`Escenarios para suite/carga (${scenarios.length})`}
                subtitle={
                  scenarios.length
                    ? `${scenarios.filter((s) => selectedScenarios[s.id]).length} seleccionados · ${collections.filter((col) => scenarios.some((s) => s.collection_id === col.id)).length} colecciones`
                    : undefined
                }
              >
                <ApiSuiteScenarioPicker
                  c={c}
                  busy={busy}
                  scenarios={scenarios}
                  collections={collections}
                  selectedScenarios={selectedScenarios}
                  scenarioWeights={scenarioWeights}
                  locustAccess={locustAccess === "granted"}
                  onSelectedChange={setSelectedScenarios}
                  onWeightChange={(id, value) => setScenarioWeights((prev) => ({ ...prev, [id]: value }))}
                  onLoadScenario={(id) => {
                    setApiTab("postman");
                    handleLoadScenario(id);
                  }}
                  onDeleteSelected={handleDeleteSelectedScenarios}
                />
              </ApiCollapsibleSection>

              <ApiSection c={c} title="Suite funcional">
                <SuiteRunnerPanel
                  c={c}
                  project={project}
                  environment={environment}
                  scenarioIds={scenarios.filter((s) => selectedScenarios[s.id]).map((s) => s.id)}
                  scenarios={scenarios}
                  envVarNames={envVarNames}
                  canRun={actionsEnabled}
                  busy={busy}
                  onError={onShowError}
                  onHint={(msg) => {
                    setHomeHint(msg);
                    if (msg.startsWith("Suite:") || msg.startsWith("Flujo:")) {
                      setSuiteHistoryRefresh((n) => n + 1);
                    }
                  }}
                />
              </ApiSection>

              <ApiSection c={c} title="Historial de suites">
                <SuiteHistoryPanel
                  c={c}
                  project={project}
                  refreshToken={suiteHistoryRefresh}
                  onError={onShowError}
                />
              </ApiSection>
            </>
          </FeatureGate>

          <FeatureGate
            c={c}
            phase={entitlementPhase}
            feature="api_locust"
            features={features}
            license={license}
            showTierUpsell={showTierUpsell}
            upsellOverlay={upsellButton("api_locust", "Desbloquea pruebas de carga con ELIA Architect")}
          >
              <ApiSection c={c} title="Prueba de carga (Locust)">
                <div style={{ fontSize: 13, color: c.muted, marginBottom: 10 }}>
                  Métricas en RAM/consola. CSV Locust opt-in automático para dashboard. PDF/HTML solo bajo demanda.
                  {modules?.api_limits?.max_load_users ? (
                    <> Límite licencia: {modules.api_limits.max_load_users} usuarios.</>
                  ) : null}
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 10 }}>
                  <div style={{ flex: "1 1 220px" }}>
                    <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>
                      Flujo guardado (opcional)
                    </label>
                    <select
                      value={loadFlowId}
                      onChange={(e) => setLoadFlowId(e.target.value)}
                      style={apiInputStyle(c, { width: "100%" })}
                    >
                      <option value="">— solo escenarios seleccionados —</option>
                      {savedLoadFlows.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  {loadFlowId && (loadFlowCounts.sql ?? 0) > 0 ? (
                    <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                      <input
                        type="checkbox"
                        checked={runSetupFlow}
                        onChange={(e) => setRunSetupFlow(e.target.checked)}
                      />
                      Ejecutar SQL de pre-carga antes de Locust
                    </label>
                  ) : null}
                </div>
                {loadFlowId && ((loadFlowCounts.sql ?? 0) > 0 || (loadFlowCounts.grpc ?? 0) > 0) ? (
                  <div
                    style={{
                      fontSize: 12,
                      padding: "8px 10px",
                      borderRadius: 8,
                      border: `1px solid ${c.border}`,
                      background: c.neutralBg,
                      marginBottom: 10,
                    }}
                  >
                    {(loadFlowCounts.sql ?? 0) > 0 ? (
                      <div>
                        Este flujo incluye {(loadFlowCounts.sql ?? 0)} paso(s) SQL.
                        {runSetupFlow
                          ? " Se ejecutarán como pre-carga; las variables resultantes alimentan la carga."
                          : " En Locust se omiten (solo HTTP/gRPC en la fase de carga)."}
                      </div>
                    ) : null}
                    {(loadFlowCounts.grpc ?? 0) > 0 ? (
                      <div style={{ marginTop: (loadFlowCounts.sql ?? 0) > 0 ? 4 : 0 }}>
                        Incluye {(loadFlowCounts.grpc ?? 0)} paso(s) gRPC — disponible en carga (ELIA Architect).
                      </div>
                    ) : null}
                  </div>
                ) : null}
                <LoadTestPanel
                  c={c}
                  project={project}
                  settings={loadSettings}
                  onChange={(patch) => setLoadSettings((prev) => ({ ...prev, ...patch }))}
                  onPreflight={handleLoadPreflight}
                  preflightBusy={preflightBusy}
                />
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 10 }}>
                  {jmxImportMeta?.load_suggestion ? (
                    <button
                      type="button"
                      onClick={() =>
                        applyJmxLoadSuggestion(jmxImportMeta.load_suggestion!, jmxImportMeta.csv_basename)
                      }
                      className={apiBtnClass()}
                    >
                      Aplicar sugerencia del .jmx
                    </button>
                  ) : null}
                  <div>
                    <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Usuarios</label>
                    <input
                      value={loadUsers}
                      onChange={(e) => setLoadUsers(e.target.value)}
                      style={apiInputStyle(c, { width: 80 })}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Tasa de subida</label>
                    <input
                      value={loadSpawn}
                      onChange={(e) => setLoadSpawn(e.target.value)}
                      style={apiInputStyle(c, { width: 80 })}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Duración</label>
                    <input
                      value={loadRunTime}
                      onChange={(e) => setLoadRunTime(e.target.value)}
                      placeholder="1m"
                      style={apiInputStyle(c, { width: 72 })}
                    />
                  </div>
                  <div style={{ flex: "1 1 200px" }}>
                    <label style={{ display: "block", fontSize: 12, color: c.muted, marginBottom: 4 }}>Host base (opcional)</label>
                    <input
                      value={loadHost}
                      onChange={(e) => setLoadHost(e.target.value)}
                      placeholder="https://api.ejemplo.com"
                      style={apiInputStyle(c, { width: "100%" })}
                    />
                  </div>
                  <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                    <input
                      type="checkbox"
                      checked={generateLoadReport}
                      onChange={(e) => setGenerateLoadReport(e.target.checked)}
                    />
                    Permitir reporte PDF al finalizar
                  </label>
                  {loadSettings.mode === "standalone" ? (
                    <button
                      type="button"
                      disabled={preflightBusy}
                      onClick={handleLoadPreflight}
                      className={apiBtnClass()}
                    >
                      Preflight
                    </button>
                  ) : null}
                  <button
                    type="button"
                    disabled={!actionsEnabled || busy}
                    onClick={handleRunLocust}
                    className={apiBtnClass(true)}
                  >
                    Ejecutar Locust
                  </button>
                </div>
                {loadRunFinished && generateLoadReport ? (
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleExportLoadReport("pdf")}
                      className={apiBtnClass(true)}
                    >
                      Generar reporte enriquecido (PDF)
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleExportLoadReport("html")}
                      className={apiBtnClass()}
                    >
                      Generar reporte enriquecido (HTML)
                    </button>
                    {loadReportFilename ? (
                      <span style={{ fontSize: 12, color: c.muted }}>Guardado: {loadReportFilename}</span>
                    ) : null}
                  </div>
                ) : null}
                <LoadMetricsPanel c={c} runId={runId} />
                <LoadHistoryComparePanel
                  c={c}
                  project={project}
                  refreshToken={historyRefresh}
                  onError={onShowError}
                  onHint={setHomeHint}
                />
                {runId ? (
                  <div style={{ marginTop: 12 }}>
                    <RunConsolePanel
                      c={c}
                      runId={runId}
                      platform="api"
                      project={project}
                      onClose={() => setRunId(null)}
                    />
                  </div>
                ) : null}
              </ApiSection>
          </FeatureGate>
        </>
      )}
      <ProjectTemplateModal
        c={c}
        open={templateModalOpen}
        onClose={() => setTemplateModalOpen(false)}
        contextPlatform="api"
        onCreated={(result) => {
          refreshHomeData();
          refreshProjects();
          const apiProj = result.projects.find((p) => p.platform === "api") ?? result.projects[0];
          if (apiProj) {
            setProject(apiProj.project);
            pendingAutoLoadRef.current = true;
            setHomeHint(`Proyecto «${apiProj.project}» listo. Colección demo y petición GET cargadas.`);
          }
        }}
      />
    </div>
  );
}
