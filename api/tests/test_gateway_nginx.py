"""Guard the gateway's runtime upstream resolution.

Regression test for the permanent-502 failure mode: a static
``proxy_pass http://api:8000/...`` is resolved once at nginx startup, so every
api container recreation (each deploy, each crash-restart) orphans the gateway
until the gateway itself restarts. All upstreams must go through variables fed
by the Docker embedded-DNS resolver instead.
"""

from __future__ import annotations

import re
from pathlib import Path

CONF = Path(__file__).resolve().parents[2] / "gateway" / "nginx.conf"


def _conf() -> str:
    return CONF.read_text()


def test_gateway_resolves_upstreams_at_runtime():
    conf = _conf()
    assert re.search(r"^\s*resolver\s+127\.0\.0\.11\b", conf, re.M) is not None


def test_no_static_proxy_pass_upstreams():
    static = re.findall(r"proxy_pass\s+https?://", _conf())
    assert static == []


def test_every_proxy_pass_uses_a_variable():
    targets = re.findall(r"proxy_pass\s+(.*?);", _conf())
    assert targets, "expected at least one proxy_pass"
    for target in targets:
        assert target.strip().startswith("$"), target
