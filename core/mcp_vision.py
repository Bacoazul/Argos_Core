"""
MCP tool: decarabia_analyze — análisis multimodal de imágenes (subagente Decarabia).

Decarabia es Gemma 4 multimodal. En vez de orquestar el workflow ComfyUI (frágil
y dependiente del grafo exacto), llamamos al MISMO modelo de visión directo por
Ollama (config.vision) — soberano, sin nube y mucho más confiable. Si en el futuro
Decarabia expone un workflow estable, se puede conmutar el backend aquí.
"""
from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path
from typing import Any, Literal

from core.config import load_model_config
from core.mcp_server import mcp
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

_TIMEOUT = 120.0

_MODE_PROMPTS = {
    "arte": (
        "Analiza esta imagen como obra visual: estilo, composición, paleta, técnica, "
        "atmósfera y posibles referencias artísticas. Sé concreto."
    ),
    "noticia": (
        "Analiza esta imagen como contenido informativo: qué muestra, contexto probable, "
        "elementos verificables y cualquier señal de manipulación. Sé objetivo."
    ),
    "general": (
        "Describe esta imagen con precisión: qué hay, qué ocurre y los detalles relevantes."
    ),
}


def _load_image_b64(image_path: str | None, image_b64: str | None) -> tuple[str | None, str | None]:
    """Devuelve (b64, error). Prioriza image_b64 si viene dado."""
    if image_b64:
        return image_b64, None
    if not image_path:
        return None, "falta image_path o image_b64"
    p = Path(image_path)
    if not p.is_file():
        return None, f"imagen no encontrada: {image_path}"
    try:
        return base64.b64encode(p.read_bytes()).decode(), None
    except Exception as e:
        return None, f"no se pudo leer la imagen: {e}"


@mcp.tool
def decarabia_analyze(
    image_path: str | None = None,
    prompt: str = "",
    mode: Literal["arte", "noticia", "general"] = "general",
    image_b64: str | None = None,
) -> dict[str, Any]:
    """
    Analiza una imagen con visión local (Gemma 4, subagente Decarabia). Sin nube.

    - image_path: ruta accesible dentro del contenedor (p.ej. en /tls/extracted/images).
    - image_b64: alternativa — la imagen en base64 directamente.
    - prompt: instrucción extra opcional (qué quieres saber de la imagen).
    - mode: "arte" | "noticia" | "general" — ajusta el enfoque del análisis.

    Devuelve {"ok": bool, "analysis": str}.
    """
    b64, err = _load_image_b64(image_path, image_b64)
    if err:
        return {"ok": False, "error": err}

    cfg = load_model_config()
    base_prompt = _MODE_PROMPTS.get(mode, _MODE_PROMPTS["general"])
    full_prompt = f"{base_prompt}\n\n{prompt}".strip() if prompt else base_prompt

    payload = json.dumps({
        "model": cfg.vision,
        "prompt": full_prompt,
        "images": [b64],
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        f"{cfg.ollama_base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            result = json.loads(r.read())
    except Exception as e:
        logger.error("decarabia_analyze falló: %s", e)
        return {"ok": False, "error": f"Ollama visión no disponible: {e}"}

    analysis = (result.get("response") or "").strip()
    if not analysis:
        return {"ok": False, "error": "el modelo no devolvió análisis"}
    return {"ok": True, "model": cfg.vision, "mode": mode, "analysis": analysis}
