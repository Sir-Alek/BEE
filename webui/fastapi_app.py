from __future__ import annotations

import os
import threading
import time
import traceback
import sys
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, Field, model_validator

from core.ui_automation.web_capture_behave_builder import WebCaptureBehaveBuilder
from core.ui_automation.web_capture_step_builder import WebCaptureStepBuilder
from ui.interfaces import BDDUserCancelled
from webui.job_manager import JobManager, Prompt
from webui.webui_adapter import WebUIAdapter


class JiraCreds(BaseModel):
    url: str = ""
    email: str = ""
    api_token: str = ""
    mode: Literal["vanilla", "xray"] = "vanilla"
    project_key: str = ""
    xray_base_url: str = ""
    target_field: str = "description"
    default_issue_key: str = ""


class ValueEdgeCreds(BaseModel):
    url: str = ""
    shared_space: str = ""
    workspace: str = ""
    tech_preview_flag: str = "true"
    login: str = ""
    user: str = ""
    password: str = ""
    default_requirement_id: str = ""


class GitCreds(BaseModel):
    provider: Literal["github", "gitlab", "azure_repos"] = "github"
    repo_url: str = ""
    branch: str = "main"
    base_path: str = "features/"
    token: str = ""


class AzureDevOpsCreds(BaseModel):
    org: str = ""
    project: str = ""
    pat: str = ""
    default_work_item_id: str = ""
    target_field: str = "System.Description"


class ConnectorProfile(BaseModel):
    id: str
    name: str
    jira: JiraCreds = Field(default_factory=JiraCreds)
    value_edge: ValueEdgeCreds = Field(default_factory=ValueEdgeCreds)
    git: GitCreds = Field(default_factory=GitCreds)
    azure_devops: AzureDevOpsCreds = Field(default_factory=AzureDevOpsCreds)


class ConnectorsDocument(BaseModel):
    version: Literal[1, 2] = 2
    profiles: List[ConnectorProfile] = Field(default_factory=list)


class EliaConnectorTestRequest(BaseModel):
    kind: Literal["jira", "value_edge", "git", "azure_devops", "jira_xray"]
    jira: JiraCreds = Field(default_factory=JiraCreds)
    value_edge: ValueEdgeCreds = Field(default_factory=ValueEdgeCreds)
    git: GitCreds = Field(default_factory=GitCreds)
    azure_devops: AzureDevOpsCreds = Field(default_factory=AzureDevOpsCreds)


class ConvertRequest(BaseModel):
    mode: Literal[
        "puppeteer_to_behave",
        "puppeteer_to_step_by_step",
        "demo",
        "puppeteer_recorder",
        # ELIA (integrations)
        "elia_jira_smoke",
        "elia_value_edge_smoke",
        "elia_gherkin_batch",
        # Building Blocks: nuevos módulos
        "mobile_recorder",
        "legacy_recorder",
        "mobile_to_behave",
        "legacy_to_behave",
        "doc_to_bdd",
        "api_to_behave",
        "api_run_behave",
        "api_load_test",
    ]
    url: Optional[str] = None
    use_ai: bool = False
    elia_use_inline_connectors: bool = False
    elia_jira: Optional[JiraCreds] = None
    elia_value_edge: Optional[ValueEdgeCreds] = None
    # Mobile recording
    platform: Optional[str] = None
    apk_path: Optional[str] = None
    device_id: Optional[str] = None
    app_package: Optional[str] = None
    app_activity: Optional[str] = None
    # Legacy recording
    window_name: Optional[str] = None
    exe_path: Optional[str] = None
    # Doc-to-BDD
    doc_files: Optional[List[str]] = None
    link_recording: Optional[str] = None
    link_scenario: Optional[str] = None
    link_scenario_by_doc: Optional[Dict[str, str]] = None
    link_recording_by_doc: Optional[Dict[str, str]] = None
    capture_api: bool = False
    api_project: Optional[str] = None
    api_traffic_path: Optional[str] = None
    api_scenario_ids: Optional[List[str]] = None
    api_feature_name: Optional[str] = None
    load_test_users: int = 5
    load_test_spawn_rate: float = 1.0
    load_test_run_time: str = "1m"
    load_test_host: str = ""

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> "ConvertRequest":
        if self.mode == "puppeteer_recorder" and not (self.url or "").strip():
            raise ValueError("url is required for puppeteer_recorder")
        if self.mode == "mobile_recorder" and not (self.device_id or "").strip():
            raise ValueError("device_id is required for mobile_recorder")
        if self.mode == "legacy_recorder":
            if not (self.window_name or "").strip() and not (self.exe_path or "").strip():
                raise ValueError("window_name or exe_path is required for legacy_recorder")
        if self.mode == "doc_to_bdd" and self.doc_files is None:
            raise ValueError("doc_files is required for doc_to_bdd")
        return self


class PromptResponseRequest(BaseModel):
    answer: Any = None


class LicenseActivateRequest(BaseModel):
    key: str


class AiPreferencesRequest(BaseModel):
    mode: str  # auto | on | off


class AiMemoryExportRequest(BaseModel):
    team_passphrase: str = Field(min_length=1)


class MobileEmulatorStartRequest(BaseModel):
    avd: str
    wait_boot: bool = True
    timeout_sec: int = Field(default=180, ge=30, le=600)


class MobileEmulatorStopRequest(BaseModel):
    device_id: Optional[str] = None


class MobileAppiumStartRequest(BaseModel):
    timeout_sec: int = Field(default=60, ge=10, le=180)


def _repo_root() -> str:
    """
    Devuelve la raíz del proyecto / directorio del bundle.

    En modo frozen (PyInstaller):
      - sys._MEIPASS apunta al directorio con los datas tanto en --onedir como --onefile.
      - Fallback: directorio del ejecutable (os.path.dirname(sys.executable)).
    En desarrollo: sube un nivel desde webui/ hasta la raíz del repo.
    """
    if getattr(sys, "frozen", False):
        # Intentar varias opciones en orden de prioridad
        meipass = getattr(sys, "_MEIPASS", None)
        for candidate in filter(None, [meipass, os.path.dirname(sys.executable)]):
            # Verificar que el candidato contiene datas reales del bundle
            if os.path.isdir(os.path.join(candidate, "resources")):
                return candidate
            if os.path.isdir(os.path.join(candidate, "frontend")):
                return candidate
        # Último recurso: primer candidato disponible aunque no tenga datas confirmadas
        if meipass and os.path.isdir(meipass):
            return meipass
        return os.path.dirname(sys.executable)
    # Desarrollo: webui/fastapi_app.py -> webui/ -> repo root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _projects_dir(platform: str = "web") -> str:
    from core.elia_paths import behave_projects_dir

    return str(behave_projects_dir(platform))

def _user_data_root() -> str:
    from core.elia_paths import ensure_user_data_root

    return str(ensure_user_data_root())


def _safe_under_user_data(*parts: str) -> str:
    """
    Defensive path join: keep ELIA batch IO under user data root.
    """
    import os

    root = os.path.abspath(_user_data_root())
    target = os.path.abspath(os.path.join(root, *[p for p in parts if p]))
    if target == root or target.startswith(root + os.sep):
        return target
    # Fallback to root if something weird was supplied.
    return root


def _require_localhost(request: Request) -> None:
    # Hardening: prevent exposing UI to other hosts.
    host = (request.client.host if request.client else "").strip()
    if host not in ("127.0.0.1", "::1", "testclient", "localhost"):
        raise HTTPException(status_code=403, detail="Forbidden: localhost only")


def _require_active_license() -> None:
    from core import elia_license

    if not elia_license.can_run_jobs():
        raise HTTPException(
            status_code=403,
            detail="Licencia: activación requerida o caducada. Introduce la clave en Configuración → Licencia.",
        )


def create_app(*, job_manager: Optional[JobManager] = None) -> FastAPI:
    from webui.error_reporting import configure_execution_logging

    configure_execution_logging()
    app = FastAPI(title="ELIA Web UI (local)")
    jm = job_manager or JobManager()
    base_dir = _repo_root()
    frontend_dist = os.path.join(base_dir, "frontend", "dist")
    logo_path = os.path.join(base_dir, "resources", "logo_elia.png")
    logo_icon_path = os.path.join(base_dir, "resources", "logo_elia_icon.png")
    logo_letters_path = os.path.join(base_dir, "resources", "logo_letras.png")
    logo_ico_path = os.path.join(base_dir, "resources", "logo_elia.ico")
    exit_flag = {"value": False}
    ui_session = {"last_ping": 0.0, "ever": False}
    elia_session_id = str(uuid.uuid4())
    app.state.elia_session_id = elia_session_id

    @app.post("/api/app/ping")
    def app_ping(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        """Latido desde cualquier pestaña UI; no apaga el servidor por inactividad."""
        ui_session["last_ping"] = time.time()
        ui_session["ever"] = True
        exit_flag["value"] = False
        return {"ok": True, "session_id": elia_session_id}

    @app.post("/api/app/exit")
    def app_exit(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        """
        Cierre explícito desde la UI (pestaña principal o ventana del navegador).
        """
        try:
            from core.beta_time_guard import record_beta_session_checkpoint
            from core.elia_license import get_license_status

            st = get_license_status()
            if st.is_beta or st.reason == "beta":
                record_beta_session_checkpoint()
        except Exception:
            pass
        exit_flag["value"] = True
        return {"ok": True}

    @app.post("/api/app/cancel-exit")
    def app_cancel_exit(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        """Anula una solicitud de salida (p. ej. recarga F5 de la pestaña de inicio)."""
        exit_flag["value"] = False
        return {"ok": True}

    @app.get("/api/app/should-exit")
    def app_should_exit(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        """Solo sale por cierre explícito de la UI; no hay apagado por tiempo."""
        return {"exit": bool(exit_flag["value"])}

    @app.get("/api/app/about")
    def app_about(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        from core._version import (
            ELIA_CONTACT_EMAIL,
            ELIA_DEVELOPER,
            ELIA_SUPPORT_EMAIL,
            ELIA_TAGLINE,
            ELIA_VERSION,
            elia_version_display,
        )
        from core.changelog import CHANGELOG_UI_ENTRY_LIMIT, load_changelog
        from webui.error_reporting import beta_feedback_url, execution_log_about_hint

        licence_path = os.path.join(base_dir, "Licence.txt")
        license_text = ""
        if os.path.isfile(licence_path):
            try:
                with open(licence_path, encoding="utf-8") as f:
                    license_text = f.read()
            except Exception:
                license_text = ""
        feedback = beta_feedback_url()
        return {
            "app_name": "ELIA",
            "session_id": elia_session_id,
            "version": ELIA_VERSION,
            "version_display": elia_version_display(),
            "developer": ELIA_DEVELOPER,
            "contact_email": ELIA_CONTACT_EMAIL,
            # Versión comercial (≥1.0): consumido por SupportContactLink en JobErrorPanel.tsx
            "support_email": ELIA_SUPPORT_EMAIL,
            "tagline": ELIA_TAGLINE,
            "license_text": license_text,
            "changelog": load_changelog(base_dir, limit=CHANGELOG_UI_ENTRY_LIMIT),
            "beta_feedback_url": feedback or None,
            "local_logs_hint": execution_log_about_hint(),
        }

    @app.get("/api/ai/status")
    def ai_status(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        """Compatibilidad: devuelve runtime; preferir /api/ai/capabilities."""
        try:
            from core import gemma_inference

            return gemma_inference.get_ai_runtime_status()
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/ai/capabilities")
    def ai_capabilities(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ai_policy import get_ai_status_payload

        return get_ai_status_payload()

    @app.get("/api/ai/preferences")
    def ai_preferences_get(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ai_policy import get_ai_status_payload

        return get_ai_status_payload()

    @app.put("/api/ai/preferences")
    def ai_preferences_put(
        req: AiPreferencesRequest,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ai_policy import get_ai_status_payload, save_preferences

        mode = (req.mode or "auto").strip().lower()
        if mode not in ("auto", "on", "off"):
            raise HTTPException(status_code=400, detail="mode debe ser auto, on u off")
        save_preferences(mode=mode)  # type: ignore[arg-type]
        return get_ai_status_payload()

    @app.get("/api/ai/memory/status")
    def ai_memory_status(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.elia_memory import memory_status

        return memory_status()

    @app.post("/api/ai/memory/export")
    def ai_memory_export(
        req: AiMemoryExportRequest,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Response:
        from core.elia_memory import export_for_team
        from core.modules_config import is_feature_enabled

        if not is_feature_enabled("team_memory_crypto"):
            raise HTTPException(
                status_code=403,
                detail="Team Memory Crypto requiere Plan Enterprise",
            )

        try:
            blob, filename = export_for_team(req.team_passphrase.strip())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return Response(
            content=blob,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/api/ai/memory/import")
    async def ai_memory_import(
        team_passphrase: str = Form(...),
        mode: str = Form(...),
        file: UploadFile = File(...),
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.elia_memory import import_from_team
        from core.modules_config import is_feature_enabled

        if not is_feature_enabled("team_memory_crypto"):
            raise HTTPException(
                status_code=403,
                detail="Team Memory Crypto requiere Plan Enterprise",
            )

        normalized_mode = (mode or "").strip().lower()
        if normalized_mode not in ("merge", "replace"):
            raise HTTPException(status_code=400, detail="mode debe ser merge o replace")
        if not (team_passphrase or "").strip():
            raise HTTPException(status_code=400, detail="team_passphrase requerida")
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Archivo vacío")
        try:
            result = import_from_team(data, team_passphrase.strip(), normalized_mode)  # type: ignore[arg-type]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No se pudo importar la memoria: {e}") from e
        return {"ok": True, **result}

    @app.get("/api/license/status")
    def license_status(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        from core import elia_license

        st = elia_license.get_license_status()
        return {
            "ok": st.ok,
            "reason": st.reason,
            "activated": st.activated,
            "machine_fingerprint": st.machine_fingerprint,
            "message": st.message,
            "can_run_jobs": elia_license.can_run_jobs(),
            "expires_at": st.expires_at,
            "duration_code": st.duration_code,
            "tier": st.tier_name,
            "tier_label": (st.tier_name or "").replace("_", " ").title() if st.tier_name else None,
            "is_beta": st.is_beta,
            "upgrade_email": st.upgrade_email,
            "features": st.features,
        }

    @app.get("/api/entitlements")
    def entitlements_status(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        from core.elia_license import get_entitlements
        from core.modules_config import get_api_module_limits, list_modules

        out = get_entitlements()
        out["api_limits"] = get_api_module_limits()
        mods = list_modules()
        for key in (
            "mobile_recording",
            "legacy_recording",
            "doc_to_bdd",
            "api_testing",
            "api_http_single",
            "api_postman_suites",
            "api_locust",
            "publishers_standard",
            "publishers_enterprise",
            "team_memory_crypto",
        ):
            if key in mods:
                out[key] = mods[key]
        return out

    @app.get("/api/modules/status")
    def modules_status(_: None = Depends(_require_localhost)) -> Dict[str, Any]:
        from core.modules_config import get_api_module_limits, list_modules

        out: Dict[str, Any] = dict(list_modules())
        out["api_limits"] = get_api_module_limits()
        return out

    @app.get("/api/recorder/preflight")
    def recorder_preflight(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        """Comprueba Google Chrome antes de iniciar puppeteer_recorder (Windows)."""
        from core.ui_automation.chrome_resolver import resolve_chrome_for_recording

        result = resolve_chrome_for_recording(base_dir)
        return result.to_dict()

    @app.get("/api/mobile/devices")
    def mobile_devices(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        """Lista dispositivos adb (físico / emulador). Android only."""
        from core.ui_automation.mobile_android import list_devices

        devices, err = list_devices()
        return {
            "ok": err is None,
            "devices": [d.to_dict() for d in devices],
            "error": err,
            "android_only": True,
        }

    @app.get("/api/mobile/foreground-app")
    def mobile_foreground_app(
        device_id: str,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ui_automation.mobile_android import detect_foreground_package

        result = detect_foreground_package(device_id)
        result["android_only"] = True
        return result

    @app.get("/api/mobile/diagnostics")
    def mobile_diagnostics(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ui_automation.mobile_android import run_diagnostics

        return run_diagnostics()

    @app.get("/api/mobile/avds")
    def mobile_avds(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ui_automation.mobile_android import list_avds

        avds, err = list_avds()
        return {"ok": err is None, "avds": avds, "error": err, "android_only": True}

    @app.get("/api/mobile/preflight")
    def mobile_preflight(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ui_automation.mobile_android import run_preflight

        return run_preflight().to_dict()

    @app.post("/api/mobile/emulator/start")
    def mobile_emulator_start(
        req: MobileEmulatorStartRequest,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ui_automation.mobile_android import start_emulator

        return start_emulator(
            req.avd,
            wait_boot=req.wait_boot,
            timeout_sec=float(req.timeout_sec),
        )

    @app.post("/api/mobile/emulator/stop")
    def mobile_emulator_stop(
        req: MobileEmulatorStopRequest,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ui_automation.mobile_android import stop_emulator

        return stop_emulator(req.device_id)

    @app.get("/api/mobile/appium/status")
    def mobile_appium_status(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ui_automation.mobile_android import get_appium_status

        return get_appium_status()

    @app.post("/api/mobile/appium/start")
    def mobile_appium_start(
        req: MobileAppiumStartRequest,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ui_automation.mobile_android import start_appium_server

        return start_appium_server(timeout_sec=float(req.timeout_sec))

    @app.post("/api/mobile/appium/stop")
    def mobile_appium_stop(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.ui_automation.mobile_android import stop_appium_server

        return stop_appium_server(only_if_started_by_elia=True)

    @app.post("/api/license/activate")
    def license_activate(
        req: LicenseActivateRequest, _: None = Depends(_require_localhost)
    ) -> Dict[str, Any]:
        from core import elia_license

        if elia_license.activate_with_key(req.key):
            st = elia_license.get_license_status()
            return {
                "ok": True,
                "message": "Licencia activada.",
                "reason": st.reason,
                "activated": st.activated,
                "can_run_jobs": elia_license.can_run_jobs(),
                "expires_at": st.expires_at,
                "duration_code": st.duration_code,
            }
        return {"ok": False, "message": "Clave no válida para esta máquina."}

    @app.get("/api/elia/connectors")
    def elia_connectors_get(
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.req_intelligence.connectors_profiles_store import load_document

        doc = load_document()
        if not doc:
            return {"version": 2, "profiles": []}
        try:
            return ConnectorsDocument.model_validate(doc).model_dump()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"connectors store invalid: {e}") from e

    @app.put("/api/elia/connectors")
    def elia_connectors_put(
        body: ConnectorsDocument,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.req_intelligence.connectors_profiles_store import normalize_document, save_document

        try:
            save_document(normalize_document(body.model_dump()))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"no se pudo guardar: {e}") from e
        return {"ok": True}

    @app.post("/api/elia/connectors/test")
    def elia_connectors_test(
        body: EliaConnectorTestRequest,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        import core.req_intelligence.integrations_service as elia_service
        from core.req_intelligence.connectors_profiles_store import normalize_profile
        from core.req_intelligence.publishers.dispatcher import PublisherDispatcher

        profile = normalize_profile(
            {
                "id": "inline-test",
                "name": "inline",
                "jira": body.jira.model_dump(),
                "value_edge": body.value_edge.model_dump(),
                "git": body.git.model_dump(),
                "azure_devops": body.azure_devops.model_dump(),
            }
        )
        dispatcher = PublisherDispatcher()
        try:
            if body.kind == "jira":
                out = elia_service.jira_smoke_test(inline=True, creds=body.jira.model_dump())
            elif body.kind == "value_edge":
                out = elia_service.value_edge_smoke_test(inline=True, creds=body.value_edge.model_dump())
            elif body.kind == "git":
                result = dispatcher.smoke_test("git", profile)
                return {"ok": result.ok, "message": result.message}
            elif body.kind == "jira_xray":
                result = dispatcher.smoke_test("jira_xray", profile)
                return {"ok": result.ok, "message": result.message}
            elif body.kind == "azure_devops":
                result = dispatcher.smoke_test("azure_devops", profile)
                return {"ok": result.ok, "message": result.message}
            else:
                raise HTTPException(status_code=400, detail=f"kind no soportado: {body.kind}")
            return {"ok": True, **out}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/jobs/convert")
    def create_job(
        req: ConvertRequest,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, str]:
        job_id = jm.create_job(mode=req.mode)

        elia_inline = bool(req.elia_use_inline_connectors)
        jira_cred_dict = req.elia_jira.model_dump() if req.elia_jira is not None else None
        ve_cred_dict = req.elia_value_edge.model_dump() if req.elia_value_edge is not None else None

        def worker() -> None:
            from core.ai_policy import resolve_use_ai

            adapter = WebUIAdapter(job_manager=jm, job_id=job_id)
            ai_resolution = resolve_use_ai()
            use_ai = ai_resolution.use_ai
            jm.add_event(job_id, "ai_policy", ai_resolution.to_dict())
            try:
                if req.mode == "demo":
                    # Simple smoke behavior: one prompt then done.
                    choice = adapter.pick_project(["Proyecto A", "Proyecto B"])
                    jm.add_event(job_id, "demo_choice", {"choice": choice})
                    jm.mark_done(job_id)
                    return

                if req.mode == "puppeteer_to_behave":
                    converter = WebCaptureBehaveBuilder(
                        base_dir,
                        adapter,
                        use_ai=use_ai,
                        link_scenario=req.link_scenario,
                    )
                    converter.convert_script()
                    jm.mark_done(job_id)
                    return

                if req.mode == "mobile_to_behave":
                    from core.modules_config import is_module_enabled
                    if not is_module_enabled("mobile_recording"):
                        jm.mark_error(
                            job_id,
                            message="Módulo no habilitado",
                            details="La grabación y conversión móvil requiere licencia mobile_recording.",
                        )
                        return
                    from core.ui_automation.recording_to_behave_converter import (
                        RecordingToBehaveConverter,
                    )

                    RecordingToBehaveConverter(
                        base_dir,
                        adapter,
                        platform="mobile",
                        use_ai=use_ai,
                        link_scenario=req.link_scenario,
                    ).convert_script()
                    jm.mark_done(job_id)
                    return

                if req.mode == "legacy_to_behave":
                    from core.modules_config import is_module_enabled
                    if not is_module_enabled("legacy_recording"):
                        jm.mark_error(
                            job_id,
                            message="Módulo no habilitado",
                            details="La grabación y conversión legacy requiere licencia legacy_recording.",
                        )
                        return
                    from core.ui_automation.recording_to_behave_converter import (
                        RecordingToBehaveConverter,
                    )

                    RecordingToBehaveConverter(
                        base_dir,
                        adapter,
                        platform="legacy",
                        use_ai=use_ai,
                        link_scenario=req.link_scenario,
                    ).convert_script()
                    jm.mark_done(job_id)
                    return

                if req.mode == "puppeteer_to_step_by_step":
                    converter = WebCaptureStepBuilder(base_dir, adapter)
                    converter.convert_script()
                    jm.mark_done(job_id)
                    return

                if req.mode == "puppeteer_recorder":
                    if not req.url:
                        jm.mark_error(job_id, message="Missing url", details="url is required for puppeteer_recorder")
                        return

                    projects_dir = _projects_dir("web")

                    import re
                    import time
                    import uuid

                    def mk_prompt(*, type: str, title: str, message: str, options=None, actions=None, payload=None) -> Prompt:
                        prompt_id = str(uuid.uuid4())
                        return Prompt(
                            prompt_id=prompt_id,
                            type=type,
                            title=title,
                            message=message,
                            options=options,
                            actions=actions,
                            payload=payload,
                        )

                    def sanitize_filename(file_name: str) -> str:
                        # Match Tk behavior from main.py
                        file_name = re.sub(r"[^\w\-_.]", "_", file_name)
                        file_name = re.sub(r"_{2,}", "_", file_name)
                        if not file_name.endswith(".js"):
                            file_name += ".js"
                        return file_name

                    def is_frozen() -> bool:
                        return getattr(sys, "frozen", False)

                    # --- Seleccionar/crear proyecto (prompts web)
                    jm.update_progress(job_id, {"stage": "Seleccionar proyecto"})

                    from webui.project_selection import prompt_project_path

                    project_path = prompt_project_path(
                        jm,
                        job_id,
                        projects_dir=projects_dir,
                        new_project_title="Nuevo Proyecto",
                        new_project_message="Nombre del proyecto (ej: MiProyecto)",
                        existing_title="Seleccionar Proyecto Existente",
                        existing_message="Selecciona un proyecto:",
                        sanitize_project_name=False,
                    )
                    if not project_path:
                        jm.cancel_job(job_id)
                        return

                    os.makedirs(project_path, exist_ok=True)
                    os.makedirs(os.path.join(project_path, "scripts"), exist_ok=True)
                    os.makedirs(os.path.join(project_path, "features"), exist_ok=True)
                    os.makedirs(os.path.join(project_path, "features", "steps"), exist_ok=True)
                    os.makedirs(os.path.join(project_path, "pages"), exist_ok=True)
                    os.makedirs(os.path.join(project_path, "resources", "data"), exist_ok=True)

                    # --- Nombre del archivo de grabación
                    jm.update_progress(job_id, {"stage": "Nombre de grabación"})
                    default_hint = "grabacion_" + time.strftime("%Y%m%d_%H%M%S")
                    ans_file = jm.create_prompt_and_wait(
                        job_id,
                        prompt=mk_prompt(
                            type="input_text",
                            title="Nombre del Archivo de Grabación",
                            message=f"Ingresa el nombre (sugerido: {default_hint})",
                        ),
                    )
                    if ans_file is None:
                        jm.cancel_job(job_id)
                        return
                    file_name = str(ans_file).strip()
                    if not file_name:
                        jm.cancel_job(job_id)
                        return
                    file_name = sanitize_filename(file_name)

                    scripts_dir = os.path.join(project_path, "scripts")
                    os.makedirs(scripts_dir, exist_ok=True)
                    output_file = os.path.join(scripts_dir, file_name)

                    from webui.web_recording_prompts import (
                        prompt_web_recording_options,
                        prompt_web_recording_proceed,
                    )

                    extras = prompt_web_recording_options(jm, job_id, mk_prompt)
                    if extras is None:
                        jm.cancel_job(job_id)
                        return
                    grabar_video, capture_api = extras

                    proceed = prompt_web_recording_proceed(jm, job_id, mk_prompt)
                    if proceed is None or not proceed:
                        jm.cancel_job(job_id)
                        return

                    # Video: se prepara el objeto pero NO se inicia aún.
                    # La grabación comienza solo cuando web_capture_engine.js señaliza BROWSER_READY,
                    # es decir, cuando el browser ya abrió la URL y está listo para interactuar.
                    video_path: Optional[str] = None
                    _recorder_holder: list = [None]  # mutable ref para el callback

                    if grabar_video:
                        from core.ui_automation.viewport_capture_writer import ViewportCaptureWriter

                        file_name_vid = "video_" + time.strftime("%Y%m%d_%H%M%S") + ".avi"
                        videos_dir = os.path.join(project_path, "grabaciones")
                        os.makedirs(videos_dir, exist_ok=True)
                        video_path = os.path.join(videos_dir, file_name_vid)

                        def _start_video_on_browser_ready() -> None:
                            """Called from a daemon thread when BROWSER_READY arrives."""
                            try:
                                r = ViewportCaptureWriter(video_path)
                                if r.start():
                                    _recorder_holder[0] = r
                                    jm.update_progress(job_id, {"stage": "Grabando video"})
                            except Exception:
                                pass

                        _on_browser_ready = _start_video_on_browser_ready
                    else:
                        _on_browser_ready = None

                    jm.update_progress(job_id, {"stage": "Preparando runtime de grabación"})

                    recorder_args = [output_file, req.url, "1" if capture_api else "0"]
                    api_traffic_path: Optional[str] = None
                    if capture_api:
                        from core.api_automation.traffic_store import traffic_path_for_web_recording

                        api_traffic_path = traffic_path_for_web_recording(project_path, output_file)
                        recorder_args.append(api_traffic_path)

                    # --- Ejecutar web_capture_engine.js
                    if is_frozen():
                        from core.ui_automation.script_runtime_host import script_runtime_host
                        try:
                            if getattr(script_runtime_host, "was_runtime_prepared_now", False):
                                jm.update_progress(job_id, {"stage": "Preparando runtime de grabación (primera vez)"})
                        except Exception:
                            pass

                        result = script_runtime_host.run_obfuscated_js(
                            "web_capture_engine.js",
                            recorder_args,
                            subprocess_timeout=None,
                            focus_automation_browser=True,
                            on_browser_ready=_on_browser_ready,
                        )
                    else:
                        from core.ui_automation.recorder_focus import run_subprocess_with_automation_focus

                        jm.update_progress(job_id, {"stage": "Ejecutando Puppeteer recorder"})
                        recorder_js_path = os.path.join(base_dir, "core", "ui_automation", "web_capture_engine.js")
                        result = run_subprocess_with_automation_focus(
                            ["node", recorder_js_path, *recorder_args],
                            cwd=base_dir,
                            timeout=None,
                            on_browser_ready=_on_browser_ready,
                        )

                    recorder_obj = _recorder_holder[0]

                    if result.returncode != 0:
                        error = result.stderr if result.stderr else "Error desconocido en Node.js"
                        raise Exception(f"Error en Puppeteer:\n{error}")

                    if not os.path.exists(output_file):
                        raise Exception("No se generó el archivo de grabación")

                    if recorder_obj:
                        try:
                            recorder_obj.stop()
                            time.sleep(0.5)
                        except Exception:
                            pass

                    from webui.conversion_result import conversion_result, file_entry

                    generated = [file_entry(output_file, "grabación")]
                    if capture_api and api_traffic_path and os.path.isfile(api_traffic_path):
                        generated.append(file_entry(api_traffic_path, "tráfico API"))
                    if video_path and os.path.isfile(video_path):
                        generated.append(file_entry(video_path, "video"))
                    jm.update_progress(
                        job_id,
                        {
                            "result_file": output_file,
                            "video_path": video_path,
                            "stage": "Listo",
                            "output_dir": os.path.dirname(output_file),
                            "generated_files": generated,
                        },
                    )
                    jm.mark_done(job_id)
                    return

                if req.mode == "elia_jira_smoke":
                    jm.update_progress(job_id, {"stage": "ELIA: Jira (smoke)"})
                    import core.req_intelligence.integrations_service as elia_service

                    try:
                        out = elia_service.jira_smoke_test(inline=elia_inline, creds=jira_cred_dict)
                        adapter.info(
                            "ELIA · Jira",
                            "Conexión OK." if out.get("ok") else "Conexión fallida.\n\nRevisa credenciales y URL.",
                        )
                        jm.add_event(job_id, "elia_jira_smoke", out)
                        jm.mark_done(job_id)
                    except Exception as e:
                        jm.mark_error(job_id, message="ELIA Jira error", details=f"{e}\n{traceback.format_exc()}")
                    return

                if req.mode == "elia_value_edge_smoke":
                    jm.update_progress(job_id, {"stage": "ELIA: Value Edge (smoke)"})
                    import core.req_intelligence.integrations_service as elia_service

                    try:
                        out = elia_service.value_edge_smoke_test(inline=elia_inline, creds=ve_cred_dict)
                        adapter.info(
                            "ELIA · Value Edge",
                            "Login OK." if out.get("ok") else "Login fallido.\n\nRevisa credenciales y URL.",
                        )
                        jm.add_event(job_id, "elia_value_edge_smoke", out)
                        jm.mark_done(job_id)
                    except Exception as e:
                        jm.mark_error(job_id, message="ELIA Value Edge error", details=f"{e}\n{traceback.format_exc()}")
                    return

                if req.mode == "elia_gherkin_batch":
                    jm.update_progress(job_id, {"stage": "ELIA: Gherkin batch (configurar)"})
                    import core.req_intelligence.integrations_service as elia_service

                    # Ask for relative folders under user data (Documents/ELIA).
                    inp_rel = jm.create_prompt_and_wait(
                        job_id,
                        prompt=Prompt(
                            prompt_id="elia_inp",
                            type="input_text",
                            title="ELIA · Gherkin batch",
                            message=(
                                "Carpeta de ENTRADA (relativa a Documentos/ELIA).\n"
                                "Debe contener archivos .json (Value Edge o Jira).\n\n"
                                "Ejemplo: gherkin_batch/inputs"
                            ),
                        ),
                    )
                    if inp_rel is None:
                        jm.cancel_job(job_id)
                        return
                    out_rel = jm.create_prompt_and_wait(
                        job_id,
                        prompt=Prompt(
                            prompt_id="elia_out",
                            type="input_text",
                            title="ELIA · Gherkin batch",
                            message=(
                                "Carpeta de SALIDA (relativa a Documentos/ELIA).\n"
                                "Aquí se generarán archivos .feature.\n\n"
                                "Ejemplo: gherkin_batch/output/features"
                            ),
                        ),
                    )
                    if out_rel is None:
                        jm.cancel_job(job_id)
                        return

                    input_dir = _safe_under_user_data(str(inp_rel).strip())
                    output_dir = _safe_under_user_data(str(out_rel).strip())
                    os.makedirs(input_dir, exist_ok=True)
                    os.makedirs(output_dir, exist_ok=True)

                    jm.update_progress(job_id, {"stage": "ELIA: Ejecutando conversión", "input_dir": input_dir, "output_dir": output_dir})
                    try:
                        elia_service.run_gherkin_batch(input_dir, output_dir, use_ai=use_ai)
                        from webui.conversion_result import files_in_directory

                        adapter.info(
                            "ELIA · Gherkin batch",
                            f"Conversión completada.\n\nEntrada:\n{input_dir}\n\nSalida:\n{output_dir}",
                            result=files_in_directory(output_dir),
                        )
                        jm.add_event(job_id, "elia_gherkin_batch", {"input_dir": input_dir, "output_dir": output_dir})
                        jm.mark_done(job_id)
                    except Exception as e:
                        jm.mark_error(job_id, message="ELIA Gherkin batch error", details=f"{e}\n{traceback.format_exc()}")
                    return

                if req.mode == "mobile_recorder":
                    from core.modules_config import is_module_enabled
                    if not is_module_enabled("mobile_recording"):
                        jm.mark_error(
                            job_id,
                            message="Módulo no habilitado",
                            details="La grabación móvil requiere licencia adicional. Contacta a soporte para activar este módulo.",
                        )
                        return
                    from core.ui_automation.mobile_recorder import MobileRecorder
                    recorder = MobileRecorder(adapter, jm, job_id)
                    recorder.record(
                        apk_path=req.apk_path or "",
                        device_id=req.device_id or "",
                        projects_dir=_projects_dir("mobile"),
                        app_package=req.app_package or "",
                        app_activity=req.app_activity or "",
                    )
                    return

                if req.mode == "legacy_recorder":
                    from core.modules_config import is_module_enabled
                    if not is_module_enabled("legacy_recording"):
                        jm.mark_error(
                            job_id,
                            message="Módulo no habilitado",
                            details="La grabación de aplicaciones legacy requiere licencia adicional. Contacta a soporte para activar este módulo.",
                        )
                        return
                    from core.ui_automation.legacy_recorder import LegacyRecorder
                    recorder = LegacyRecorder(adapter, jm, job_id)
                    recorder.record(
                        window_name=req.window_name or "",
                        exe_path=req.exe_path or "",
                        projects_dir=_projects_dir("legacy"),
                    )
                    return

                if req.mode == "api_to_behave":
                    from core.modules_config import is_module_enabled
                    from core.ai_policy import resolve_use_ai

                    if not is_module_enabled("api_testing"):
                        jm.mark_error(job_id, message="Módulo no habilitado", details="api_testing requiere licencia vigente.")
                        return
                    from core.api_automation.api_to_behave_converter import convert_traffic_to_feature, write_api_feature
                    from core.api_automation.traffic_store import load_scenario

                    project = (req.api_project or "DefaultApi").strip()
                    use_ai = resolve_use_ai().use_ai
                    jm.update_progress(job_id, {"stage": "Convirtiendo a Behave API"})
                    try:
                        if req.api_traffic_path and os.path.isfile(req.api_traffic_path):
                            feature = convert_traffic_to_feature(
                                project,
                                req.api_traffic_path,
                                feature_name=req.api_feature_name,
                                use_ai=use_ai,
                            )
                        else:
                            requests = [load_scenario(project, sid) for sid in (req.api_scenario_ids or [])]
                            if not requests:
                                raise ValueError("Sin escenarios ni tráfico para convertir")
                            feature = write_api_feature(
                                project,
                                requests,
                                feature_name=req.api_feature_name or "Escenario API",
                                use_ai=use_ai,
                            )
                        jm.update_progress(job_id, {"stage": "Listo", "feature_file": feature, "use_ai": use_ai})
                        adapter.info("ELIA · API → Behave", f"Feature generado:\n{feature}")
                        jm.mark_done(job_id)
                    except Exception as e:
                        jm.mark_error(job_id, message="Error API → Behave", details=f"{e}\n{traceback.format_exc()}")
                    return

                if req.mode == "api_run_behave":
                    from core.modules_config import is_module_enabled
                    from core.test_runner.run_launcher import build_behave_command, build_run_env, prepare_project
                    from core.test_runner.runner_service import test_runner_service

                    if not is_module_enabled("api_testing"):
                        jm.mark_error(job_id, message="Módulo no habilitado", details="api_testing requiere licencia vigente.")
                        return

                    project = (req.api_project or "DefaultApi").strip()
                    project_path = prepare_project("api", project)
                    feature = req.api_feature_name or "features"
                    cmd = build_behave_command(feature)
                    run_id = test_runner_service.start(
                        kind="behave_api",
                        command=cmd,
                        cwd=project_path,
                        env=build_run_env("api", generate_evidence=True, headless=True),
                    )
                    jm.update_progress(job_id, {"stage": "Ejecutando Behave API", "run_id": run_id})
                    while True:
                        run = test_runner_service.get(run_id)
                        if run is None or run.state != "running":
                            break
                        time.sleep(0.5)
                    run = test_runner_service.get(run_id)
                    if run and run.state == "done":
                        jm.update_progress(job_id, {"stage": "Completado", "run_id": run_id})
                        jm.mark_done(job_id)
                    else:
                        jm.mark_error(
                            job_id,
                            message="Behave API falló",
                            details="\n".join((run.lines if run else [])[-40:]),
                        )
                    return

                if req.mode == "api_load_test":
                    from core.modules_config import is_module_enabled
                    if not is_module_enabled("api_testing"):
                        jm.mark_error(job_id, message="Módulo no habilitado", details="api_testing requiere licencia vigente.")
                        return
                    from core.api_automation.locust_generator import write_locustfile
                    from core.api_automation.traffic_store import list_scenarios, load_scenario
                    from core.elia_paths import behave_projects_dir
                    from core.test_runner.runner_service import test_runner_service

                    project = (req.api_project or "DefaultApi").strip()
                    project_path = str(behave_projects_dir("api") / project)
                    scenarios = [load_scenario(project, s["id"]) for s in list_scenarios(project)]
                    locust_path = write_locustfile(project_path, scenarios, host=req.load_test_host or "")
                    try:
                        import locust  # noqa: F401
                    except ImportError:
                        jm.mark_error(job_id, message="Locust no instalado", details="pip install locust")
                        return
                    cmd = [
                        sys.executable,
                        "-m",
                        "locust",
                        "-f",
                        os.path.basename(locust_path),
                        "--headless",
                        "-u",
                        str(req.load_test_users),
                        "-r",
                        str(req.load_test_spawn_rate),
                        "-t",
                        req.load_test_run_time,
                    ]
                    if req.load_test_host:
                        cmd.extend(["--host", req.load_test_host])
                    run_id = test_runner_service.start(kind="locust", command=cmd, cwd=project_path)
                    jm.update_progress(job_id, {"stage": "Ejecutando Locust", "run_id": run_id})
                    while True:
                        run = test_runner_service.get(run_id)
                        if run is None or run.state != "running":
                            break
                        time.sleep(0.5)
                    run = test_runner_service.get(run_id)
                    if run and run.state == "done":
                        jm.mark_done(job_id)
                    else:
                        jm.mark_error(job_id, message="Locust falló", details="\n".join((run.lines if run else [])[-40:]))
                    return

                if req.mode == "doc_to_bdd":
                    from core.modules_config import is_module_enabled
                    if not is_module_enabled("doc_to_bdd"):
                        jm.mark_error(
                            job_id,
                            message="Módulo no habilitado",
                            details="La conversión de documentos a BDD requiere licencia adicional.",
                        )
                        return
                    from core.req_intelligence.bdd_doc_converter import BDDDocConverter
                    from core.req_intelligence.doc_ingestion import WordIngester, ExcelIngester
                    from core.elia_paths import doc_features_dir

                    jm.update_progress(job_id, {"stage": "Cargando documentos"})

                    doc_files = req.doc_files or []
                    if not doc_files:
                        jm.mark_error(job_id, message="Sin documentos", details="No se proporcionaron archivos para procesar.")
                        return

                    chunks = []
                    for fpath in doc_files:
                        if not os.path.isfile(fpath):
                            continue
                        ext = os.path.splitext(fpath)[1].lower()
                        if ext == ".docx":
                            ingester = WordIngester()
                            chunks.extend(ingester.ingest(fpath))
                        elif ext == ".xlsx":
                            ingester = ExcelIngester()
                            chunks.extend(ingester.ingest(fpath))

                    if not chunks:
                        jm.mark_error(
                            job_id,
                            message="Sin contenido",
                            details=(
                                "Los documentos no produjeron filas procesables. "
                                "En Excel, revisa que la matriz tenga columnas de caso/pasos/resultado "
                                "(aunque esté en la 2ª hoja o más abajo); la 1ª hoja puede ser portada o índice."
                            ),
                        )
                        return

                    jm.update_progress(job_id, {"stage": f"Convirtiendo {len(chunks)} bloques a BDD…"})

                    from core.elia_paths import doc_features_dir

                    output_dir = str(doc_features_dir())
                    converter = BDDDocConverter(use_ai=use_ai, ui=adapter)
                    result = converter.convert_chunks(
                        chunks,
                        output_dir,
                        link_scenario=req.link_scenario,
                        link_scenario_by_doc=req.link_scenario_by_doc,
                        link_recording=req.link_recording,
                        link_recording_by_doc=req.link_recording_by_doc,
                    )

                    summary = (
                        f"Conversión completada.\n\n"
                        f"Features creados: {result.features_created}\n"
                        f"Escenarios generados: {result.scenarios_generated}\n"
                        f"Escenarios vinculados (merge): {result.scenarios_linked}\n"
                        f"Con errores (revisión manual): {result.errors_logged}\n\n"
                        f"Archivos en:\n{output_dir}"
                    )
                    if result.errors_logged > 0:
                        summary += f"\n\nRevisa _elia_errors.log para detalles de los {result.errors_logged} bloques con error."

                    from webui.conversion_result import files_in_directory

                    adapter.info(
                        "ELIA · Doc to BDD",
                        summary,
                        result=files_in_directory(output_dir),
                    )
                    jm.add_event(job_id, "doc_to_bdd", {
                        "features_created": result.features_created,
                        "scenarios_generated": result.scenarios_generated,
                        "errors_logged": result.errors_logged,
                        "output_dir": output_dir,
                        "link_recording": req.link_recording,
                        "link_scenario": req.link_scenario,
                        "scenarios_linked": result.scenarios_linked,
                    })
                    jm.mark_done(job_id)
                    return

                jm.mark_error(job_id, message="Unknown mode", details=str(req.mode))
            except BDDUserCancelled:
                jm.cancel_job(job_id)
            except Exception as e:
                jm.mark_error(job_id, message="Job failed", details=f"{e}\n{traceback.format_exc()}")

        threading.Thread(target=worker, daemon=True).start()
        return {"job_id": job_id}

    @app.get("/api/jobs/{job_id}")
    def get_job(
        job_id: str,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        try:
            return jm.get_job_summary(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")

    @app.get("/api/jobs/{job_id}/events")
    def get_job_events(
        job_id: str,
        since: int = 0,
        limit: int = 200,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        try:
            payload = jm.get_job_events(job_id, limit=limit, since=since)
            return {"job_id": job_id, **payload}
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")

    @app.get("/api/jobs/{job_id}/error-report")
    def download_job_error_report(
        job_id: str,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Response:
        from webui.error_reporting import build_error_report, load_job_error_report

        try:
            summary = jm.get_job_summary(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")

        if summary.get("state") != "error" or not summary.get("error"):
            raise HTTPException(status_code=400, detail="job has no exportable error")

        content: str | None = None
        try:
            job = jm.get_job(job_id)
            with job.lock:
                raw = job.error or {}
                if raw:
                    content = build_error_report(
                        job_id=job_id,
                        mode=job.mode,
                        error_msg=str(raw.get("message", "Error desconocido")),
                        traceback_str=str(raw.get("details") or ""),
                        events=list(job.events),
                    )
        except KeyError:
            pass
        if not content:
            content = load_job_error_report(job_id)
        if not content:
            raise HTTPException(status_code=404, detail="error report not available")

        short_id = job_id.replace("-", "")[:8]
        headers = {"Content-Disposition": f'attachment; filename="elia_error_{short_id}.txt"'}
        return Response(content=content, media_type="text/plain; charset=utf-8", headers=headers)

    @app.post("/api/jobs/{job_id}/prompts/{prompt_id}/response")
    def answer_prompt(
        job_id: str,
        prompt_id: str,
        req: PromptResponseRequest,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        try:
            jm.answer_prompt(job_id, prompt_id=prompt_id, answer=req.answer)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        return {"ok": True}

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(
        job_id: str,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        try:
            jm.get_job(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        jm.cancel_job(job_id)
        return {"ok": True}

    @app.post("/api/jobs/{job_id}/stop-recording")
    def stop_recording(
        job_id: str,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        try:
            jm.get_job(job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="job not found")
        jm.request_recording_stop(job_id)
        return {"ok": True}

    # -----------------------
    # Req Intelligence: upload + scenarios
    # -----------------------
    @app.post("/api/req/upload-docs")
    async def upload_docs(
        files: List[UploadFile] = File(...),
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        import shutil
        from core.elia_paths import uploads_tmp_dir

        tmp_dir = uploads_tmp_dir()
        saved: List[Dict[str, str]] = []
        allowed_exts = {".docx", ".xlsx", ".json"}
        for upload in files:
            name = upload.filename or "file"
            ext = os.path.splitext(name)[1].lower()
            if ext not in allowed_exts:
                continue
            dest = os.path.join(str(tmp_dir), name)
            # Avoid path traversal
            dest = os.path.normpath(dest)
            if not dest.startswith(str(tmp_dir)):
                continue
            with open(dest, "wb") as f:
                shutil.copyfileobj(upload.file, f)
            saved.append({"name": name, "path": dest, "ext": ext})
        return {"ok": True, "files": saved}

    @app.get("/api/req/scenarios")
    def get_scenarios(
        project: Optional[str] = None,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.req_intelligence.feature_scanner import scan_project_scenarios
        from core.elia_paths import behave_project_search_roots, doc_features_dir

        results: List[Dict[str, str]] = []
        dirs_to_scan: List[str] = []

        if project:
            for root in behave_project_search_roots():
                candidate = os.path.join(str(root), project)
                if os.path.isdir(candidate):
                    dirs_to_scan.append(candidate)
        else:
            for root in behave_project_search_roots():
                try:
                    for entry in os.listdir(str(root)):
                        full = os.path.join(str(root), entry)
                        if os.path.isdir(full):
                            dirs_to_scan.append(full)
                except OSError:
                    pass

        # Also scan doc_features dir
        dirs_to_scan.append(str(doc_features_dir()))

        for d in dirs_to_scan:
            try:
                for ref in scan_project_scenarios(d):
                    results.append({
                        "feature_file": ref.feature_file,
                        "scenario_name": ref.scenario_name,
                        "line": str(ref.line_number),
                    })
            except Exception:
                pass

        return {"scenarios": results}

    @app.get("/api/req/recordings")
    def get_recordings(
        project: Optional[str] = None,
        _: None = Depends(_require_localhost),
        __: None = Depends(_require_active_license),
    ) -> Dict[str, Any]:
        from core.elia_paths import behave_project_search_roots
        from core.req_intelligence.recording_scanner import scan_all_recordings_from_roots

        roots = [str(p) for p in behave_project_search_roots()]
        refs = scan_all_recordings_from_roots(roots, project_filter=project)
        return {
            "recordings": [
                {
                    "project": r.project,
                    "file_name": r.file_name,
                    "file_path": r.file_path,
                    "platform": r.platform,
                    "label": r.label,
                }
                for r in refs
            ]
        }

    from webui.api_routes import register_api_routes
    from webui.req_publish_routes import register_req_publish_routes
    from webui.run_routes import register_run_routes

    register_api_routes(app, require_localhost=_require_localhost, require_active_license=_require_active_license)
    register_run_routes(app, require_localhost=_require_localhost, require_active_license=_require_active_license)
    register_req_publish_routes(
        app, require_localhost=_require_localhost, require_active_license=_require_active_license
    )

    # -----------------------
    # SPA static serving
    # -----------------------
    @app.get("/")
    def spa_root(_: None = Depends(_require_localhost)) -> Any:
        if not os.path.exists(frontend_dist):
            frozen = getattr(sys, "frozen", False)
            hint = (
                f"<p><small>Bundle path checked: <code>{frontend_dist}</code></small></p>"
                if frozen
                else "<p>Run: <code>cd frontend && npm install && npm run build</code></p>"
            )
            return HTMLResponse(f"<h3>Frontend not built.</h3>{hint}")
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/logo.png")
    def logo_png(_: None = Depends(_require_localhost)) -> Any:
        if not os.path.exists(logo_path):
            raise HTTPException(status_code=404, detail="logo not found")
        return FileResponse(logo_path, media_type="image/png")

    @app.get("/logo-icon.png")
    def logo_icon_png(_: None = Depends(_require_localhost)) -> Any:
        path = logo_icon_path if os.path.exists(logo_icon_path) else logo_path
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="logo icon not found")
        return FileResponse(path, media_type="image/png")

    @app.get("/logo-letters.png")
    def logo_letters_png(_: None = Depends(_require_localhost)) -> Any:
        path = logo_letters_path if os.path.exists(logo_letters_path) else logo_path
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="logo letters not found")
        return FileResponse(path, media_type="image/png")

    @app.get("/favicon.ico")
    def favicon_ico(_: None = Depends(_require_localhost)) -> Any:
        if not os.path.exists(logo_ico_path):
            raise HTTPException(status_code=404, detail="favicon not found")
        return FileResponse(logo_ico_path, media_type="image/x-icon")

    @app.get("/{path:path}")
    def spa_catchall(path: str, _: None = Depends(_require_localhost)) -> Any:
        # Ensure we never hijack /api routes.
        if path.startswith("api/") or path == "api":
            raise HTTPException(status_code=404, detail="Not found")
        if not os.path.exists(frontend_dist):
            return HTMLResponse(
                f"<h3>Frontend not built.</h3>"
                f"<p><small>{frontend_dist}</small></p>"
            )

        target = os.path.join(frontend_dist, path)
        if os.path.isfile(target):
            return FileResponse(target)

        # SPA fallback: serve index.html for any other route.
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    return app


# Default app for `uvicorn webui.fastapi_app:app`
app = create_app()

