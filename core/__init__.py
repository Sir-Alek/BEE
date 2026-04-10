from __future__ import annotations

"""
Paquete core: carga de assets (recorder JS) para runtime y empaquetado.

- recorder.js: en release se prefiere `recorder.obfuscated.js` (pipeline javascript-obfuscator).
- Compatibilidad: archivos legacy `*.enc` (BEE_PROTECTED) si aún existen.
"""
import os
import base64
import zlib
import sys

class Deobfuscator:
    _instance = None
    _cache = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _resolve_js_path(self, file_name: str) -> str | None:
        """recorder.js -> recorder.obfuscated.js si existe."""
        if file_name != "recorder.js":
            return None
        base = os.path.dirname(__file__)
        obf = os.path.join(base, "recorder.obfuscated.js")
        if os.path.isfile(obf):
            return obf
        return None

    def _read_plain(self, relative_path: str) -> bytes | None:
        """Lee bytes desde core/ (desarrollo o _MEIPASS)."""
        base = os.path.dirname(__file__)
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "") or ""
            candidates = [
                os.path.join(meipass, "core", relative_path),
                os.path.join(meipass, relative_path),
                os.path.join(base, relative_path),
            ]
        else:
            candidates = [os.path.join(base, relative_path)]

        for p in candidates:
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    return f.read()
        return None

    def load_file(self, relative_path):
        """Carga bytes: JS ofuscado plano, o .enc legacy."""
        if relative_path in self._cache:
            return self._cache[relative_path]

        # 1) JS: preferir artefacto ofuscado (mismo nombre lógico recorder.js)
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

        # 2) Legacy .enc
        try:
            enc_file_path = None
            if getattr(sys, "frozen", False):
                base_path = getattr(sys, "_MEIPASS", "") or ""
                possible_locations = [
                    os.path.join(base_path, "core", relative_path + ".enc"),
                    os.path.join(base_path, relative_path + ".enc"),
                    os.path.join(os.path.dirname(sys.executable), "core", relative_path + ".enc"),
                    os.path.join(os.getcwd(), "core", relative_path + ".enc"),
                    os.path.join(os.path.dirname(__file__), relative_path + ".enc"),
                ]
                for location in possible_locations:
                    if os.path.exists(location):
                        enc_file_path = location
                        break
            else:
                enc_file_path = os.path.join(os.path.dirname(__file__), relative_path + ".enc")

            if enc_file_path and os.path.exists(enc_file_path):
                with open(enc_file_path, "rb") as f:
                    lines = f.readlines()
                    if len(lines) >= 2 and b"BEE_PROTECTED" in lines[0]:
                        encoded_content = lines[1].strip()
                        decoded_b64 = base64.b64decode(encoded_content)
                        original_content = zlib.decompress(decoded_b64)
                        self._cache[relative_path] = original_content
                        return original_content
        except Exception:
            pass

        raise FileNotFoundError(f"No se encontró ni plano ni .enc: {relative_path}")


def get_core_file(file_name):
    return Deobfuscator.get_instance().load_file(file_name)
