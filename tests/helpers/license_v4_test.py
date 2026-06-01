"""Helpers para firmar claves v4 en tests unitarios."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "license-tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from license_sign import sign_beta_global_license, sign_machine_license  # noqa: E402

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TEST_PRIVATE = _FIXTURES / "license_test_private.pem"
TEST_KID = "test"


def build_test_v4_key(
    machine_fp: str,
    *,
    tier_code: str = "ENT",
    duration: str = "365D",
    issue_ts: int | None = None,
) -> str:
    key, _ = sign_machine_license(
        private_key_path=TEST_PRIVATE,
        kid=TEST_KID,
        machine_fp=machine_fp,
        tier_code=tier_code,
        duration=duration,
        issue_ts=issue_ts,
    )
    return key


def build_test_v4_beta_global(*, exp_ts: int) -> str:
    key, _ = sign_beta_global_license(
        private_key_path=TEST_PRIVATE,
        kid=TEST_KID,
        exp_ts=exp_ts,
    )
    return key
