from __future__ import annotations

"""
Paquete core: carga de assets (web capture engine JS) para runtime y empaquetado.

web_capture_engine.js: prioridad `ELIA_RECORDER_JS`, `web_capture_engine.obfuscated.js`,
otros `web_capture_engine.*.js`, y `web_capture_engine.js` plano.
"""
import os
import sys


class _CaptureEngineLoader:
    _instance = None
    _cache = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _capture_engine_candidate_dirs(self) -> list[str]:
        base = os.path.dirname(__file__)
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
        if file_name != "web_capture_engine.js":
            return None
        env_name = (os.environ.get("ELIA_RECORDER_JS") or "").strip()
        candidates: list[str] = []
        if env_name:
            if os.path.isabs(env_name):
                candidates.append(env_name)
            else:
                for d in self._capture_engine_candidate_dirs():
                    candidates.append(os.path.join(d, env_name))
        for name in (
            "web_capture_engine.obfuscated.js",
            "web_capture_engine.test.js",
            "web_capture_engine.min.js",
        ):
            for d in self._capture_engine_candidate_dirs():
                candidates.append(os.path.join(d, name))
        for d in self._capture_engine_candidate_dirs():
            try:
                for fn in sorted(os.listdir(d)):
                    if not fn.startswith("web_capture_engine") or not fn.endswith(".js"):
                        continue
                    if fn == "web_capture_engine.js":
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
                os.path.join(meipass, "core", "ui_automation", relative_path),
                os.path.join(meipass, "core", relative_path),
                os.path.join(meipass, relative_path),
                os.path.join(base, "ui_automation", relative_path),
                os.path.join(base, relative_path),
            ]
            if relative_path == "web_capture_engine.js":
                for extra in (
                    "web_capture_engine.obfuscated.js",
                    "web_capture_engine.test.js",
                    "web_capture_engine.min.js",
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

        raise FileNotFoundError(f"No se encontró web capture engine JS: {relative_path}")


def get_core_file(file_name):
    return _CaptureEngineLoader.get_instance().load_file(file_name)
