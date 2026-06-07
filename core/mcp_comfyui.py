"""
MCP tool: anima_generate — genera imágenes anime con Anima vía ComfyUI.

ComfyUI corre en el host (host.docker.internal:8188); si está apagado se despierta
vía Windows Bridge. La imagen se guarda en un volumen rw y se devuelve la ruta —
no se devuelven bytes crudos por MCP.

El prompt lo provee el cliente MCP (un LLM capaz): puede ser lenguaje natural o
tags danbooru. No hacemos una segunda llamada a un modelo de tagging aquí (eso
vive en el bot); mantiene la tool autónoma y predecible.
"""
from __future__ import annotations

import json
import os
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from core.bridge_client import BRIDGE_TOKEN, BRIDGE_URL
from core.mcp_server import mcp
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://host.docker.internal:8188")
_OUTPUT_DIR = Path(os.getenv("ANIMA_OUTPUT_DIR", "/data/argos/generated"))
_POLL_INTERVAL = 2.0
_POLL_TIMEOUT = 180.0
_WAKE_TIMEOUT = 120.0
_WAKE_INTERVAL = 5.0

_NEG_DEFAULT = (
    "worst quality, low quality, lowres, bad anatomy, bad hands, "
    "missing fingers, extra digits, fewer digits, cropped, jpeg artifacts, "
    "signature, watermark, username, blurry"
)

_WORKFLOW: dict = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "anima-base-v1.0.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_06b_base.safetensors", "type": "sd3"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
    "5": {"class_type": "CLIPTextEncode", "inputs": {"text": _NEG_DEFAULT, "clip": ["2", 0]}},
    "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
    "7": {"class_type": "KSampler", "inputs": {
        "seed": 0, "control_after_generate": "randomize", "steps": 35, "cfg": 4.5,
        "sampler_name": "er_sde", "scheduler": "simple", "denoise": 1.0,
        "model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "anima", "images": ["8", 0]}},
}


def _comfyui_up() -> bool:
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=3.0) as r:
            return r.status == 200
    except Exception:
        return False


def _wake_comfyui() -> str | None:
    """Despierta ComfyUI vía Bridge. Devuelve error string o None si OK."""
    req = urllib.request.Request(
        f"{BRIDGE_URL}/launch/comfyui",
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
        if _comfyui_up():
            return None
    return f"ComfyUI no respondió tras {_WAKE_TIMEOUT:.0f}s"


@mcp.tool
def anima_generate(
    prompt: str,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 35,
    cfg: float = 4.5,
) -> dict[str, Any]:
    """
    Genera una imagen anime con Anima (ComfyUI local, RTX 5090). Sin nube.

    - prompt: descripción o tags danbooru de la imagen (el cliente hace el prompt
      engineering). Ej: "masterpiece, best quality, 1girl, white hair, red eyes".
    - negative: tags negativos opcionales (si vacío usa un negativo por defecto).
    - width/height/steps/cfg: parámetros de muestreo.

    Despierta ComfyUI si está apagado. Guarda el PNG en disco y devuelve su ruta.
    """
    if not prompt or not prompt.strip():
        return {"ok": False, "error": "prompt vacío"}

    if not _comfyui_up():
        err = _wake_comfyui()
        if err:
            return {"ok": False, "error": err}

    wf = json.loads(json.dumps(_WORKFLOW))
    wf["4"]["inputs"]["text"] = prompt.strip()
    wf["5"]["inputs"]["text"] = negative or _NEG_DEFAULT
    wf["6"]["inputs"]["width"] = max(256, min(2048, width))
    wf["6"]["inputs"]["height"] = max(256, min(2048, height))
    wf["7"]["inputs"]["seed"] = random.randint(0, 2**32 - 1)
    wf["7"]["inputs"]["steps"] = max(1, min(80, steps))
    wf["7"]["inputs"]["cfg"] = cfg

    payload = json.dumps({"prompt": wf}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt", data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as r:
            result = json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": f"ComfyUI no disponible: {e}"}

    prompt_id = result.get("prompt_id")
    if not prompt_id:
        return {"ok": False, "error": f"ComfyUI no retornó prompt_id: {result}"}

    img_bytes = _poll_image(prompt_id)
    if img_bytes is None:
        return {"ok": False, "error": f"timeout o sin imagen ({_POLL_TIMEOUT:.0f}s)"}

    try:
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        fname = f"anima_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{prompt_id[:8]}.png"
        out_path = _OUTPUT_DIR / fname
        out_path.write_bytes(img_bytes)
    except Exception as e:
        return {"ok": False, "error": f"no se pudo guardar la imagen: {e}"}

    return {"ok": True, "path": str(out_path), "filename": fname, "bytes": len(img_bytes)}


def _poll_image(prompt_id: str) -> bytes | None:
    """Polling del history hasta tener la imagen. None si timeout."""
    deadline = time.monotonic() + _POLL_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(_POLL_INTERVAL)
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=5.0) as r:
                history = json.loads(r.read())
        except Exception:
            continue

        entry = history.get(prompt_id, {})
        if not entry.get("status", {}).get("completed"):
            continue

        for node_out in entry.get("outputs", {}).values():
            images = node_out.get("images", [])
            if not images:
                continue
            img = images[0]
            url = (
                f"{COMFYUI_URL}/view"
                f"?filename={urllib.parse.quote(img['filename'])}"
                f"&subfolder={urllib.parse.quote(img.get('subfolder', ''))}"
                f"&type={img.get('type', 'output')}"
            )
            try:
                with urllib.request.urlopen(url, timeout=15.0) as r:
                    return r.read()
            except Exception:
                return None
    return None
