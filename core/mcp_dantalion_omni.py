"""
MCP tool: dantalion_analyze_video — comprensión audio-visual real de video
(subproyecto omni de Dantalion). Ve frames y escucha audio en la misma
pasada (Qwen3-Omni-30B-A3B-Instruct-AWQ-4bit, servido on-demand en un
contenedor WSL2 aparte — puerto 8610).

No reimplementa el motor acá: esto es un cliente HTTP delgado, igual que
mcp_vision.py llama a Ollama o mcp_baael.py llama al transcriber.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from core.mcp_server import mcp
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

_OMNI_URL = os.getenv("DANTALION_OMNI_URL", "http://host.docker.internal:8610")


@mcp.tool
def dantalion_analyze_video(
    url: str | None = None,
    path: str | None = None,
    question: str | None = None,
) -> dict[str, Any]:
    """
    Analiza un video completo — ve los frames Y escucha el audio en la misma
    pasada (no transcripción + captioning pegados por separado). Útil para:
    guías paso a paso de grabaciones de pantalla, entender qué pasa en un
    clip/reel, o encontrar el momento exacto de algo dentro de un video largo.

    Args:
        url: URL del video (YouTube, reel, etc. — se descarga vía yt-dlp).
        path: alternativa — ruta local ya accesible por el servicio omni.
        question: qué querés saber. Si se omite, devuelve una línea de
            tiempo general fundiendo lo visual y lo verbal en cada evento.

    Returns:
        dict con {"ok", "title", "duration_seconds", "chunked", "result"}.
        Si el motor no está cargado y no hay VRAM libre suficiente, "ok"
        viene en False con el error explicando qué liberar primero
        (gemma4:26b en Ollama o el AGENT en llama-swap :8090).
    """
    if not url and not path:
        return {"ok": False, "error": "falta url o path"}

    try:
        r = httpx.post(
            f"{_OMNI_URL}/analyze",
            json={"url": url, "path": path, "question": question, "save": True},
            timeout=1800,  # la primera carga del modelo + análisis de video puede tardar mucho
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        logger.warning("dantalion_analyze_video: error %s: %s", e.response.status_code, e.response.text[:300])
        return {"ok": False, "error": e.response.text[:500]}
    except Exception as e:
        logger.error("dantalion_analyze_video falló: %s", e)
        return {"ok": False, "error": f"servicio omni no disponible: {e}"}
