"""Sanitización de tráfico API capturado (tokens, cookies sensibles)."""
from __future__ import annotations

import re
from typing import Dict, Iterable

_SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "proxy-authorization",
    }
)

_REDACT_PATTERNS = (
    (re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9\-._~+/]+=*"), r"\1REDACTED"),
    (re.compile(r'(?i)("(?:password|token|secret|api_key)"\s*:\s*")[^"]*(")'), r'\1REDACTED\2'),
)


def sanitize_header_value(name: str, value: str) -> str:
    key = (name or "").strip().lower()
    if key in _SENSITIVE_HEADERS:
        return "REDACTED"
    out = value or ""
    for pattern, repl in _REDACT_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {k: sanitize_header_value(k, v) for k, v in headers.items()}


def sanitize_body(text: str | None, *, max_len: int = 50000) -> str | None:
    if text is None:
        return None
    out = text
    for pattern, repl in _REDACT_PATTERNS:
        out = pattern.sub(repl, out)
    if len(out) > max_len:
        return out[: max_len - 20] + "\n...[truncado]"
    return out


def is_noise_url(url: str, extra: Iterable[str] = ()) -> bool:
    lower = (url or "").lower()
    noise = (
        "google-analytics.com",
        "googletagmanager.com",
        "facebook.com/tr",
        "hotjar.com",
        "segment.io",
        "doubleclick.net",
        "clarity.ms",
    )
    return any(n in lower for n in (*noise, *extra))
