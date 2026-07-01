"""Catálogo y creación de proyectos desde plantillas empaquetadas (P1 onboarding)."""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.elia_paths import BEHAVE_PLATFORMS, behave_projects_dir
from core.test_runner.behave_support import BEHAVE_PLATFORMS as RUNNER_PLATFORMS
from core.test_runner.behave_support import ensure_platform_behave_support

_PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-.]{0,62}[A-Za-z0-9]$|^[A-Za-z0-9]$")


@dataclass
class CreatedProject:
    platform: str
    project: str
    path: str


@dataclass
class TemplateCreateResult:
    ok: bool
    template_id: str
    projects: List[CreatedProject] = field(default_factory=list)
    checklist: List[str] = field(default_factory=list)
    message: str = ""


def templates_root() -> Path:
    from core.test_runner.behave_support import elia_base_dir

    return Path(elia_base_dir()) / "resources" / "project_templates"


def normalize_project_name(raw: str) -> str:
    name = str(raw or "").strip()
    if not name:
        return ""
    cleaned = re.sub(r"[^\w\-_.]", "_", name)
    cleaned = cleaned.strip("._-")
    return cleaned[:64]


def validate_project_name(name: str) -> None:
    n = normalize_project_name(name)
    if not n:
        raise ValueError("Nombre de proyecto requerido")
    if not _PROJECT_NAME_RE.match(n):
        raise ValueError(
            "Nombre no válido: use letras, números, guiones o guiones bajos (3–64 caracteres recomendado)"
        )
    lowered = n.lower()
    if lowered in {"con", "prn", "aux", "nul"} or lowered.startswith("com") and len(lowered) == 4:
        raise ValueError("Nombre de proyecto reservado")


def _template_dir(template_id: str) -> Path:
    tid = (template_id or "").strip()
    if not tid or ".." in tid or "/" in tid or "\\" in tid:
        raise ValueError("Identificador de plantilla no válido")
    path = templates_root() / tid
    if not path.is_dir():
        raise FileNotFoundError(f"Plantilla no encontrada: {tid}")
    return path


def _load_manifest(template_id: str) -> Dict[str, Any]:
    manifest_path = _template_dir(template_id) / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest.json ausente en plantilla {template_id}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest.json inválido")
    data.setdefault("id", template_id)
    return data


def _public_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    kind = str(manifest.get("kind") or "single")
    out: Dict[str, Any] = {
        "id": str(manifest.get("id") or ""),
        "version": int(manifest.get("version") or 1),
        "kind": kind,
        "name": str(manifest.get("name") or manifest.get("id") or ""),
        "description": str(manifest.get("description") or ""),
        "default_project_name": str(manifest.get("default_project_name") or "ELIA-Demo"),
        "estimated_minutes": int(manifest.get("estimated_minutes") or 5),
        "checklist": [str(x) for x in (manifest.get("checklist") or []) if str(x).strip()],
        "prerequisites": [str(x) for x in (manifest.get("prerequisites") or []) if str(x).strip()],
    }
    if kind == "single":
        out["platform"] = str(manifest.get("platform") or "web")
    else:
        components = manifest.get("components") or []
        out["components"] = [
            {
                "template": str(c.get("template") or ""),
                "platform": str(c.get("platform") or ""),
                "name_suffix": str(c.get("name_suffix") or ""),
            }
            for c in components
            if isinstance(c, dict)
        ]
    return out


def list_project_templates() -> List[Dict[str, Any]]:
    root = templates_root()
    if not root.is_dir():
        return []
    items: List[Dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        manifest_path = child / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = _load_manifest(child.name)
            items.append(_public_manifest(manifest))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return items


def _project_root(platform: str, project: str) -> Path:
    plat = (platform or "").strip().lower()
    if plat not in BEHAVE_PLATFORMS:
        raise ValueError(f"Plataforma no soportada: {platform}")
    return behave_projects_dir(plat) / project


def _project_exists(platform: str, project: str) -> bool:
    return _project_root(platform, project).is_dir()


def _write_project_metadata(dest: Path, *, template_id: str, template_version: int) -> None:
    meta_dir = dest / ".elia"
    meta_dir.mkdir(parents=True, exist_ok=True)
    from core._version import ELIA_VERSION

    doc = {
        "template_id": template_id,
        "template_version": template_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "elia_version": ELIA_VERSION,
    }
    (meta_dir / "project.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def _copy_payload(template_id: str, dest: Path) -> None:
    payload = _template_dir(template_id) / "payload"
    if not payload.is_dir():
        raise FileNotFoundError(f"payload/ ausente en plantilla {template_id}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError(f"El proyecto ya existe: {dest.name}")
    shutil.copytree(payload, dest, dirs_exist_ok=False)


def _finalize_platform_project(platform: str, dest: Path, *, template_id: str, template_version: int) -> None:
    plat = platform.lower()
    if plat in RUNNER_PLATFORMS:
        ensure_platform_behave_support(dest, plat)
    if plat == "api":
        from core.api_automation.traffic_store import ensure_api_project

        ensure_api_project(dest.name)
        try:
            from core.api_automation.scenario_index import rebuild_index

            rebuild_index(dest.name)
        except Exception:
            pass
    _write_project_metadata(dest, template_id=template_id, template_version=template_version)
    errors = validate_template_project(plat, dest)
    if errors:
        raise RuntimeError("; ".join(errors))


def validate_template_project(platform: str, project_path: Path) -> List[str]:
    """Comprueba que un proyecto generado desde plantilla puede ejecutarse."""
    root = Path(project_path)
    plat = (platform or "").strip().lower()
    errors: List[str] = []

    if plat in RUNNER_PLATFORMS:
        for rel in ("utils/button_functions.py", "utils/env_manager.py", "features/environment.py"):
            if not (root / rel).is_file():
                errors.append(f"Falta {rel}")

    if plat == "web":
        for rel in (
            "features/demo_login.feature",
            "features/steps/demo_login_steps.py",
            "pages/login_page.py",
            "resources/data/Login demo Sauce Demo.json",
        ):
            if not (root / rel).is_file():
                errors.append(f"Falta {rel}")

    if plat == "api":
        scenario = root / "scenarios" / "demo" / "get_post_1.json"
        if not scenario.is_file():
            errors.append("Falta escenario demo get_post_1.json")
        env_file = root / "environments" / "dev.json"
        if not env_file.is_file():
            errors.append("Falta environments/dev.json")

    return errors


def _create_single(template_id: str, project_name: str) -> CreatedProject:
    manifest = _load_manifest(template_id)
    kind = str(manifest.get("kind") or "single")
    if kind != "single":
        raise ValueError(f"La plantilla {template_id} no es de proyecto único")
    platform = str(manifest.get("platform") or "web").lower()
    name = normalize_project_name(project_name) or normalize_project_name(
        str(manifest.get("default_project_name") or "ELIA-Demo")
    )
    validate_project_name(name)
    if _project_exists(platform, name):
        raise FileExistsError(f"Ya existe un proyecto «{name}» en behave/{platform}/")

    dest = _project_root(platform, name)
    _copy_payload(template_id, dest)
    version = int(manifest.get("version") or 1)
    _finalize_platform_project(platform, dest, template_id=template_id, template_version=version)
    return CreatedProject(platform=platform, project=name, path=str(dest.resolve()))


def create_project_from_template(template_id: str, project_name: str) -> TemplateCreateResult:
    manifest = _load_manifest(template_id)
    kind = str(manifest.get("kind") or "single")

    if kind == "multi":
        base = normalize_project_name(project_name) or normalize_project_name(
            str(manifest.get("default_project_name") or "ELIA-Demo")
        )
        validate_project_name(base)
        components = manifest.get("components") or []
        if not components:
            raise ValueError("Plantilla multi sin componentes")

        created: List[CreatedProject] = []
        for comp in components:
            if not isinstance(comp, dict):
                continue
            child_id = str(comp.get("template") or "").strip()
            suffix = str(comp.get("name_suffix") or "").strip()
            child_name = f"{base}-{suffix}" if suffix else base
            child = _create_single(child_id, child_name)
            created.append(child)

        if not created:
            raise ValueError("No se pudo crear ningún componente de la plantilla multi")

        checklist = [str(x) for x in (manifest.get("checklist") or []) if str(x).strip()]
        return TemplateCreateResult(
            ok=True,
            template_id=template_id,
            projects=created,
            checklist=checklist,
            message=f"Proyectos creados: {', '.join(p.project for p in created)}",
        )

    project = _create_single(template_id, project_name)
    checklist = [str(x) for x in (manifest.get("checklist") or []) if str(x).strip()]
    return TemplateCreateResult(
        ok=True,
        template_id=template_id,
        projects=[project],
        checklist=checklist,
        message=f"Proyecto «{project.project}» listo en behave/{project.platform}/",
    )
