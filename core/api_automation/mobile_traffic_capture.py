"""Captura tráfico API desde emulador Android (WebView/Chrome)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from core.api_automation.traffic_store import ingest_capture_dict, save_traffic_file, api_traffic_path_for_recording


def _parse_performance_log(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    idx = 0
    for item in entries:
        try:
            msg = json.loads(item.get("message", "{}"))
        except (json.JSONDecodeError, TypeError):
            continue
        inner = msg.get("message") or {}
        if inner.get("method") != "Network.responseReceived":
            continue
        params = inner.get("params") or {}
        response = params.get("response") or {}
        url = str(response.get("url") or "")
        if not url.startswith("http"):
            continue
        idx += 1
        out.append(
            {
                "id": f"mobile-req-{idx}",
                "method": str(response.get("requestHeaders", {}).get(":method") or "GET"),
                "url": url,
                "request_headers": {},
                "response_status": int(response.get("status") or 0) or 200,
                "response_body": None,
            }
        )
    return out


def capture_from_appium_driver(driver, *, source_url: str = "") -> Optional[str]:
    """Intenta leer performance logs del driver Appium (Chrome/WebView)."""
    try:
        logs = driver.get_log("performance")
    except Exception:
        return None
    entries = _parse_performance_log(logs)
    if not entries:
        return None
    capture = ingest_capture_dict({"version": 1, "entries": entries}, source_url=source_url)
    return capture.to_dict()


def save_mobile_capture(
    api_project: str,
    recording_basename: str,
    capture_dict: Dict[str, Any],
) -> str:
    from core.api_automation.models import ApiTrafficCapture

    path = str(api_traffic_path_for_recording(api_project, recording_basename))
    cap = ApiTrafficCapture.from_dict(capture_dict)
    save_traffic_file(path, cap)
    return path
