"""
Stub del subprocess de web_capture_engine.js para E2E e integración sin Chrome real.

Simula BROWSER_READY y termina con código 0, como si el usuario cerrara el navegador.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

_STUB_INSTALLED = False


def fake_run_subprocess_with_automation_focus(
    cmd: list[str],
    *,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    timeout: Optional[float] = None,
    focus_delay_sec: float = 2.2,
    on_browser_ready: Optional[Callable[[], None]] = None,
) -> subprocess.CompletedProcess[str]:
    del cwd, env, timeout, focus_delay_sec
    if on_browser_ready:
        try:
            on_browser_ready()
        except Exception:
            pass
    if len(cmd) >= 3:
        out = Path(cmd[2])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f"// stub recording\nmodule.exports = [];\n", encoding="utf-8")
    stdout = (
        "BROWSER_READY\n"
        'WINDOW_INFO:{"x":0,"y":0,"width":1280,"height":720}\n'
        "[stub] recorder finished\n"
    )
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=stdout, stderr="")


def install_puppeteer_recorder_stub() -> None:
    """Parchea run_subprocess_with_automation_focus en el módulo de enfoque."""
    global _STUB_INSTALLED
    if _STUB_INSTALLED:
        return
    import core.ui_automation.recorder_focus as rf

    rf.run_subprocess_with_automation_focus = fake_run_subprocess_with_automation_focus  # type: ignore[assignment]
    _STUB_INSTALLED = True


def install_chrome_preflight_stub(*, chrome_path: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe") -> None:
    """Fuerza preflight OK cuando Chrome no está instalado (CI)."""
    from core.ui_automation import chrome_resolver as cr

    def _stub(**kwargs: Any) -> cr.ChromeResolveResult:
        del kwargs
        return cr.ChromeResolveResult(ok=True, chrome_path=chrome_path, source="e2e-stub")

    cr.resolve_chrome_for_recording = _stub  # type: ignore[assignment]


def maybe_install_chrome_preflight_stub(base_dir: str) -> None:
    """Solo stub si la resolución real falla."""
    from core.ui_automation import chrome_resolver as cr

    if cr.resolve_chrome_for_recording(base_dir=base_dir).ok:
        return
    install_chrome_preflight_stub()
