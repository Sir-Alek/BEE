"""
Servidor FastAPI aislado para pruebas E2E (Playwright).

Datos bajo tests/e2e/.runtime — no toca %LOCALAPPDATA%\\ELIA del desarrollador.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# tests/e2e/scripts/e2e_serve.py -> repo root
ROOT = Path(__file__).resolve().parents[3]
E2E_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PORT = int(os.environ.get("ELIA_E2E_PORT", "8765"))
HOST = "127.0.0.1"
RUNTIME = Path(os.environ.get("ELIA_E2E_RUNTIME", E2E_ROOT / ".runtime"))
RUNTIME.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("LOCALAPPDATA", str(RUNTIME / "LocalAppData"))
os.environ.setdefault("TEMP", str(RUNTIME / "Temp"))
os.environ.setdefault("TMP", str(RUNTIME / "Temp"))
os.environ.setdefault("ELIA_USER_DATA", str(RUNTIME / "UserData"))
os.environ["ELIA_SKIP_LICENSE"] = ""

Path(os.environ["LOCALAPPDATA"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["TEMP"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["ELIA_USER_DATA"]).mkdir(parents=True, exist_ok=True)


def _isolated_backup_paths() -> list[Path]:
    la = Path(os.environ["LOCALAPPDATA"])
    tmp = Path(os.environ["TEMP"])
    return [
        tmp / "etil_sys_metrics.db",
        la / "Microsoft" / "Windows" / "WebCache" / ".win_telemetry_cache",
        la / "ELIA" / ".wgx_state_cache",
    ]


def _prepare_isolated_license_store() -> None:
    from core import elia_license as lic

    lic._get_hidden_backup_paths = _isolated_backup_paths  # type: ignore[method-assign]
    lic.revoke_license_local(clear_backups=True)


_prepare_isolated_license_store()


def _install_e2e_stubs() -> None:
    if os.environ.get("ELIA_E2E_STUB_PUPPETEER", "1").strip().lower() in ("0", "false", "no"):
        return
    from tests.support.recorder_stub import (
        install_puppeteer_recorder_stub,
        maybe_install_chrome_preflight_stub,
    )

    install_puppeteer_recorder_stub()
    maybe_install_chrome_preflight_stub(str(ROOT))


_install_e2e_stubs()

if __name__ == "__main__":
    import uvicorn

    from webui.fastapi_app import create_app

    print(f"ELIA E2E server on http://{HOST}:{PORT}", flush=True)
    print(f"  LOCALAPPDATA={os.environ['LOCALAPPDATA']}", flush=True)
    print(f"  ELIA_USER_DATA={os.environ['ELIA_USER_DATA']}", flush=True)
    uvicorn.run(create_app(), host=HOST, port=PORT, log_level="warning")
