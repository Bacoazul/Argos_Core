"""
MCP tool: frigate_cam — control de cámaras Frigate (subagente Amon / VigilancAI).

Frigate corre en WSL2 (host.docker.internal:5000) con auth por cookie. go2rtc es
on-demand: se arranca/para vía Windows Bridge al activar/desactivar. Snapshots se
guardan en disco y se devuelve la ruta.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import httpx

from core.bridge_client import BRIDGE_TOKEN, BRIDGE_URL
from core.mcp_server import mcp
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

FRIGATE_URL = os.getenv("FRIGATE_INT_URL", "http://host.docker.internal:5000")
FRIGATE_USER = os.getenv("FRIGATE_USER", "admin")
FRIGATE_PASS = os.getenv("FRIGATE_PASS", "")
_DEFAULT_CAMERA = os.getenv("FRIGATE_DEFAULT_CAMERA", "c200")
_SNAP_DIR = Path(os.getenv("FRIGATE_SNAP_DIR", "/data/argos/snapshots"))


async def _cookie(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{FRIGATE_URL}/api/login",
        json={"user": FRIGATE_USER, "password": FRIGATE_PASS},
    )
    r.raise_for_status()
    return r.cookies.get("frigate_token", "")


async def _config_set(client: httpx.AsyncClient, cookie: str, camera: str, field: str, value: object) -> bool:
    payload = {
        "requires_restart": 0,
        "update_topic": f"config/cameras/{camera}/{field}",
        "config_data": {"cameras": {camera: {field: value}}},
    }
    r = await client.put(
        f"{FRIGATE_URL}/api/config/set", json=payload, cookies={"frigate_token": cookie}
    )
    return r.json().get("success", False)


async def _go2rtc(action: str) -> bool:
    """action: 'start' | 'stop'. True si quedó en el estado deseado."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(
                f"{BRIDGE_URL}/go2rtc/{action}", headers={"X-Bridge-Token": BRIDGE_TOKEN}
            )
            running = r.json().get("running", False)
            return running if action == "start" else not running
    except Exception as e:
        logger.warning("go2rtc/%s error: %s", action, e)
        return False


@mcp.tool
async def frigate_cam(
    action: Literal["list", "snapshot", "enable", "disable"],
    camera: str | None = None,
) -> dict[str, Any]:
    """
    Controla las cámaras de vigilancia Frigate (subagente Amon). Sin nube.

    action:
      - "list"     : lista cámaras y su estado (grabación/detección/snapshots).
      - "snapshot" : guarda el último frame de la cámara y devuelve la ruta.
      - "enable"   : activa grabación+detección+snapshots (arranca go2rtc).
      - "disable"  : desactiva todo (apaga go2rtc).

    camera: nombre de la cámara (default "c200"). Para "list" se ignora.
    """
    cam = camera or _DEFAULT_CAMERA

    try:
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            cookie = await _cookie(client)

            if action == "list":
                cfg_r = await client.get(f"{FRIGATE_URL}/api/config", cookies={"frigate_token": cookie})
                cams = cfg_r.json().get("cameras", {})
                return {
                    "ok": True,
                    "cameras": {
                        name: {
                            "record": c.get("record", {}).get("enabled", False),
                            "detect": c.get("detect", {}).get("enabled", False),
                            "snapshots": c.get("snapshots", {}).get("enabled", False),
                        }
                        for name, c in cams.items()
                    },
                }

            if action == "snapshot":
                r = await client.get(
                    f"{FRIGATE_URL}/api/{cam}/latest.jpg", cookies={"frigate_token": cookie}
                )
                if r.status_code != 200:
                    return {"ok": False, "error": f"no hay snapshot para {cam} (HTTP {r.status_code})"}
                _SNAP_DIR.mkdir(parents=True, exist_ok=True)
                fname = f"{cam}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                out = _SNAP_DIR / fname
                out.write_bytes(r.content)
                return {"ok": True, "path": str(out), "filename": fname, "bytes": len(r.content)}

            if action in ("enable", "disable"):
                enabled = action == "enable"
                if enabled and not await _go2rtc("start"):
                    return {"ok": False, "error": "no pude iniciar go2rtc (¿bridge arriba?)"}

                results = []
                for field in ("record", "detect", "snapshots"):
                    results.append(await _config_set(client, cookie, cam, field, {"enabled": enabled}))

                if not enabled:
                    await _go2rtc("stop")

                if all(results):
                    return {"ok": True, "camera": cam, "enabled": enabled}
                return {"ok": False, "error": "Frigate no confirmó todos los cambios", "camera": cam}

        return {"ok": False, "error": f"acción no reconocida: {action}"}
    except httpx.ConnectError:
        return {"ok": False, "error": "no puedo conectar con Frigate (¿está corriendo?)"}
    except Exception as e:
        msg = f"{type(e).__name__}: {e}".strip().rstrip(":")
        logger.error("frigate_cam falló: %s", msg)
        return {"ok": False, "error": msg}
