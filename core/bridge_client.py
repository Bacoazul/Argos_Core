"""
Argos Core - Windows Bridge HTTP client.

Cliente autónomo para el Windows Bridge (:8189). Replica el patrón de
_Asmodeus/skills/amon.py SIN importarlo — Argos y Asmodeus son contenedores
distintos. Mantiene Argos independiente.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from utils.logger_config import get_argos_logger

logger = get_argos_logger()

BRIDGE_URL = os.getenv("WINDOWS_BRIDGE_URL", "http://host.docker.internal:8189")
BRIDGE_TOKEN = os.getenv("BRIDGE_TOKEN", "asmodeus-bridge-2026")
_TIMEOUT = 8.0


def bridge_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST JSON al bridge con token. Nunca lanza — devuelve {'ok': False, 'error': ...}."""
    req = urllib.request.Request(
        f"{BRIDGE_URL}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Bridge-Token": BRIDGE_TOKEN},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return json.loads(r.read())
    except Exception as ex:
        logger.error("bridge POST %s falló: %s", path, ex)
        return {"ok": False, "error": str(ex)}


def bridge_get(path: str) -> dict[str, Any]:
    """GET JSON del bridge. Nunca lanza."""
    req = urllib.request.Request(f"{BRIDGE_URL}{path}", headers={"X-Bridge-Token": BRIDGE_TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return json.loads(r.read())
    except Exception as ex:
        logger.error("bridge GET %s falló: %s", path, ex)
        return {"ok": False, "error": str(ex)}
