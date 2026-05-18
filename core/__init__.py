from __future__ import annotations

"""
Paquete core: carga de assets (recorder JS) para runtime y empaquetado.

recorder.js: prioridad `ELIA_RECORDER_JS`, `recorder.obfuscated.js`, otros `recorder.*.js`, `recorder.js` plano.
"""
import os
import sys


class _RecorderLoader:
    _instance = None
    _cache = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _recorder_js_candidate_dirs(self) -> list[str]:
        base = os.path.dirname(__file__)
        # ui_automation/ es la ubicación canónica del JS; core/ raíz se conserva como fallback.
        out = [os.path.join(base, "ui_automation"), base]
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "") or ""
            if meipass:
                out.append(os.path.join(meipass, "core", "ui_automation"))
                out.append(os.path.join(meipass, "core"))
                out.append(meipass)
        seen: set[str] = set()
        uniq: list[str] = []
        for d in out:
            if d and d not in seen:
                seen.add(d)
                uniq.append(d)
        return uniq

    def _resolve_js_path(self, file_name: str) -> str | None:
        if file_name != "recorder.js":
            return None
        env_name = (os.environ.get("ELIA_RECORDER_JS") or "").strip()
        candidates: list[str] = []
        if env_name:
            if os.path.isabs(env_name):
                candidates.append(env_name)
            else:
                for d in self._recorder_js_candidate_dirs():
                    candidates.append(os.path.join(d, env_name))
        for name in (
            "recorder.obfuscated.js",
            "recorder.test.js",
            "recorder.min.js",
        ):
            for d in self._recorder_js_candidate_dirs():
                candidates.append(os.path.join(d, name))
        for d in self._recorder_js_candidate_dirs():
            try:
                for fn in sorted(os.listdir(d)):
                    if not fn.startswith("recorder") or not fn.endswith(".js"):
                        continue
                    if fn == "recorder.js":
                        continue
                    p = os.path.join(d, fn)
                    if p not in candidates:
                        candidates.append(p)
            except OSError:
                pass
        for p in candidates:
            if p and os.path.isfile(p):
                return p
        return None

    def _read_plain(self, relative_path: str) -> bytes | None:
        base = os.path.dirname(__file__)
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "") or ""
            candidates = [
                # ui_automation/ es la ubicación canónica del JS en el bundle
                os.path.join(meipass, "core", "ui_automation", relative_path),
                os.path.join(meipass, "core", relative_path),
                os.path.join(meipass, relative_path),
                os.path.join(base, "ui_automation", relative_path),
                os.path.join(base, relative_path),
            ]
            if relative_path == "recorder.js":
                for extra in (
                    "recorder.obfuscated.js",
                    "recorder.test.js",
                    "recorder.min.js",
                ):
                    candidates.insert(0, os.path.join(meipass, "core", "ui_automation", extra))
                    candidates.insert(1, os.path.join(meipass, "core", extra))
                env_name = (os.environ.get("ELIA_RECORDER_JS") or "").strip()
                if env_name:
                    candidates.insert(
                        0,
                        env_name if os.path.isabs(env_name) else os.path.join(meipass, "core", "ui_automation", env_name),
                    )
        else:
            candidates = [
                os.path.join(base, "ui_automation", relative_path),
                os.path.join(base, relative_path),
            ]

        for p in candidates:
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    return f.read()
        return None

    def load_file(self, relative_path: str) -> bytes:
        if relative_path in self._cache:
            return self._cache[relative_path]

        js_alt = self._resolve_js_path(relative_path)
        if js_alt:
            with open(js_alt, "rb") as f:
                data = f.read()
                self._cache[relative_path] = data
                return data

        plain = self._read_plain(relative_path)
        if plain is not None:
            self._cache[relative_path] = plain
            return plain

        raise FileNotFoundError(f"No se encontró recorder JS: {relative_path}")


def get_core_file(file_name):
    return _RecorderLoader.get_instance().load_file(file_name)


# ---------------------------------------------------------------------------
# Compatibilidad retroactiva: los imports `from core.X import Y` siguen
# funcionando aunque X se haya movido a core/ui_automation/ o req_intelligence/.
#
# Se usa un proxy lazy para no cargar todos los módulos al iniciar la aplicación.
# ---------------------------------------------------------------------------
import importlib as _importlib


class _LazyModuleAlias:
    """Proxy que importa el módulo real sólo al primer acceso de atributo."""

    __slots__ = ("_target", "_module")

    def __init__(self, target: str) -> None:
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_module", None)

    def _resolve(self):
        mod = object.__getattribute__(self, "_module")
        if mod is None:
            mod = _importlib.import_module(object.__getattribute__(self, "_target"))
            object.__setattr__(self, "_module", mod)
        return mod

    def __getattr__(self, name: str):
        return getattr(self._resolve(), name)

    def __repr__(self) -> str:
        return f"<LazyAlias → {object.__getattribute__(self, '_target')}>"


_COMPAT_ALIASES: dict = {
    # core/ui_automation/
    "core.puppeteer_script_converter": "core.ui_automation.puppeteer_script_converter",
    "core.step_by_step_converter":     "core.ui_automation.step_by_step_converter",
    "core.flow_analyzer":              "core.ui_automation.flow_analyzer",
    "core.locator_healer":             "core.ui_automation.locator_healer",
    "core.node_wrapper":               "core.ui_automation.node_wrapper",
    "core.recorder_focus":             "core.ui_automation.recorder_focus",
    "core.video_recorder":             "core.ui_automation.video_recorder",
    # core/req_intelligence/
    "core.gherkin_converter":          "core.req_intelligence.gherkin_converter",
    "core.jira_extractor":             "core.req_intelligence.jira_extractor",
    "core.value_edge_extractor":       "core.req_intelligence.value_edge_extractor",
    "core.integrations_service":       "core.req_intelligence.integrations_service",
    "core.integrations_config_loader": "core.req_intelligence.integrations_config_loader",
    "core.connectors_profiles_store":  "core.req_intelligence.connectors_profiles_store",
}

for _alias_old, _alias_new in _COMPAT_ALIASES.items():
    if _alias_old not in sys.modules:
        sys.modules[_alias_old] = _LazyModuleAlias(_alias_new)  # type: ignore[assignment]
