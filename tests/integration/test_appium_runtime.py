"""
Runtime Appium (nightly / manual).

Ejecutar:
  set ELIA_RUN_NIGHTLY=1
  set ELIA_APPIUM_URL=http://127.0.0.1:4723
  python tests/run_integration.py
"""
from __future__ import annotations

import importlib.util
import importlib.util
import os
import sys
import unittest

from tests.paths import REPO_ROOT
from tests.support.markers import nightly_enabled


def _load_mobile_recorder():
    path = REPO_ROOT / "core" / "ui_automation" / "mobile_recorder.py"
    spec = importlib.util.spec_from_file_location("mobile_recorder_runtime", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _appium_url() -> str:
    return (os.environ.get("ELIA_APPIUM_URL") or "http://127.0.0.1:4723").strip().rstrip("/")


@unittest.skipUnless(nightly_enabled(), "Requiere ELIA_RUN_NIGHTLY=1")
class TestAppiumRuntimeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        mr = _load_mobile_recorder()
        url = _appium_url()
        host_port = url.replace("http://", "").replace("https://", "")
        if ":" in host_port:
            host, port_s = host_port.split(":", 1)
            port = int(port_s.split("/")[0])
        else:
            host, port = host_port, 4723
        if not mr._check_appium_server(host=host, port=port):
            raise unittest.SkipTest(
                f"Appium no accesible en {url} — arranca el servidor o define ELIA_APPIUM_URL",
            )
        cls.mr = mr
        cls.appium_url = url

    def test_appium_status_endpoint(self) -> None:
        import http.client
        from urllib.parse import urlparse

        parsed = urlparse(self.appium_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 4723
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/status")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)

    def test_appium_client_import_and_capabilities_shape(self) -> None:
        if importlib.util.find_spec("appium") is None:
            self.skipTest("Appium-Python-Client no instalado")
        webdriver_mod, options_cls = self.mr._import_appium_client()
        self.assertTrue(callable(getattr(webdriver_mod, "Remote", None)))
        opts = options_cls()
        caps = opts.to_capabilities() if hasattr(opts, "to_capabilities") else {}
        self.assertIsInstance(caps, dict)


if __name__ == "__main__":
    unittest.main()
