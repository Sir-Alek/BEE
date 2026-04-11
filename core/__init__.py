from __future__ import annotations

"""
Paquete core: carga de assets (recorder JS) para runtime y empaquetado.

recorder.js: prioridad `BEE_RECORDER_JS`, `recorder.obfuscated.js`, otros `recorder.*.js`, `recorder.js` plano.
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
        out = [base]
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "") or ""
            if meipass:
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
        env_name = (os.environ.get("BEE_RECORDER_JS") or "").strip()
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
                os.path.join(meipass, "core", relative_path),
                os.path.join(meipass, relative_path),
                os.path.join(base, relative_path),
            ]
            if relative_path == "recorder.js":
                for extra in (
                    "recorder.obfuscated.js",
                    "recorder.test.js",
                    "recorder.min.js",
                ):
                    candidates.insert(0, os.path.join(meipass, "core", extra))
                env_name = (os.environ.get("BEE_RECORDER_JS") or "").strip()
                if env_name:
                    candidates.insert(
                        0,
                        env_name if os.path.isabs(env_name) else os.path.join(meipass, "core", env_name),
                    )
        else:
            candidates = [os.path.join(base, relative_path)]

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
