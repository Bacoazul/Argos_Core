"""
MCP tool: andras_train — lanza entrenamiento de LoRA en Andras via UI Next.js.

Andras es el wrapper de entrenamiento de LoRAs para Krea 2 basado en
ai-toolkit (ostris). La UI Next.js corre en :8675; si está apagada se
despierta vía Windows Bridge.

El config lo provee el cliente MCP. Campos típicos:
  - dataset_path: ruta al dataset (imágenes + captions)
  - output_name: nombre del LoRA de salida (sin extensión)
  - steps: pasos de entrenamiento (default 1000)
  - model: modelo base (default "krea2")
Consultar la UI en :8675 para el schema exacto una vez instalada.
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

from core.bridge_client import BRIDGE_TOKEN, BRIDGE_URL
from core.mcp_server import mcp
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

ANDRAS_UI_URL = "http://host.docker.internal:8675"
_WAKE_TIMEOUT = 60.0
_WAKE_INTERVAL = 5.0


def _andras_ui_up() -> bool:
    try:
        with urllib.request.urlopen(f"{ANDRAS_UI_URL}/", timeout=3.0) as r:
            return r.status == 200
    except Exception:
        return False


def _wake_andras() -> str | None:
    """Despierta la Andras UI vía Bridge. Devuelve error string o None si OK."""
    req = urllib.request.Request(
        f"{BRIDGE_URL}/launch/andras_ui",
        data=b"{}",
        headers={"Content-Type": "application/json", "X-Bridge-Token": BRIDGE_TOKEN},
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as r:
            result = json.loads(r.read())
    except Exception as e:
        return f"Windows Bridge no disponible: {e}"

    if result.get("status") == "already_running":
        return None

    deadline = time.monotonic() + _WAKE_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(_WAKE_INTERVAL)
        if _andras_ui_up():
            return None
    return f"Andras UI no respondió tras {_WAKE_TIMEOUT:.0f}s"


@mcp.tool
def andras_train(
    config: dict,
) -> dict[str, Any]:
    """
    Lanza entrenamiento de LoRA en Andras (ai-toolkit local, RTX 5090). Sin nube.

    - config: configuración del entrenamiento. Campos típicos:
        - name: nombre del job (requerido)
        - job_config: config YAML del trainer (dataset_path, output_name, steps, model...)
        - gpu_ids: IDs de GPU (default "0")
      Consultar la UI en :8675 para el schema exacto de configuración.

    Despierta la Andras UI si está apagada. Envía el job a /api/jobs.
    """
    if not isinstance(config, dict):
        return {"ok": False, "error": "config debe ser un dict"}

    if not _andras_ui_up():
        err = _wake_andras()
        if err:
            return {"ok": False, "error": err}

    payload = json.dumps({
        "name": config.get("name", "andras-lora-job"),
        "job_config": config.get("job_config", config),
        "gpu_ids": config.get("gpu_ids", "0"),
    }).encode()
    req = urllib.request.Request(
        f"{ANDRAS_UI_URL}/api/jobs",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15.0) as r:
            result = json.loads(r.read())
        logger.info("Andras job creado: %s", config.get("name", "?"))
        return {"ok": True, **result}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"Andras /api/jobs respondió {e.code}: {e}"}
    except Exception as e:
        logger.error("Andras train error: %s", e)
        return {
            "ok": False,
            "error": f"Andras UI no disponible: {e}",
            "ui_url": ANDRAS_UI_URL,
        }
