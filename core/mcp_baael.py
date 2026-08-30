"""
MCP tool: baael_transcribe — baja audio de un video/reel corto (YouTube,
Instagram, TikTok, Facebook, X, etc. vía yt-dlp) y lo transcribe usando el
servicio Whisper de Baael (telegram-summarizer/transcriber, puerto 9000).

No reimplementa nada de Baael: yt-dlp corre acá mismo (dependencia liviana,
sin modelo propio), y la transcripción se delega al transcriber ya existente
para no duplicar el modelo Whisper en GPU.
"""
from __future__ import annotations

import os
import tempfile
from typing import Any

import httpx
import yt_dlp

from core.mcp_server import mcp
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

_TRANSCRIBER_URL = os.getenv(
    "BAAEL_TRANSCRIBER_URL", "http://host.docker.internal:9000/transcribe"
)


def _extract_meta(info: dict) -> dict[str, Any]:
    return {
        "title": info.get("title") or None,
        "author": info.get("uploader") or info.get("channel") or None,
        "description": info.get("description") or info.get("text") or None,
        "duration": info.get("duration_string") or None,
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
    }


@mcp.tool
def baael_transcribe(url: str, language: str | None = None) -> dict[str, Any]:
    """
    Baja el audio de un video corto (YouTube, Instagram Reels, TikTok,
    Facebook, X, etc.) y lo transcribe con el Whisper de Baael.

    Útil para resumir/investigar reels y clips cortos que no traen
    subtítulos propios (Instagram/Facebook casi nunca los exponen).

    Args:
        url: URL del video/reel.
        language: código de idioma opcional para forzar la transcripción
            (ej. "es", "en"). Si se omite, Whisper autodetecta.

    Returns:
        dict con title, author, description, duration, view_count,
        like_count, transcript y language. Si no se pudo transcribir
        (falla de descarga o de Whisper), transcript queda en None y
        se devuelve igual la metadata disponible.
    """
    meta: dict[str, Any] = {}
    transcript = None
    detected_language = None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "quiet": True,
                "format": "bestaudio/best",
                "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "64",
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url)
                meta = _extract_meta(info)

            audio_path = os.path.join(tmpdir, "audio.mp3")

            try:
                with open(audio_path, "rb") as f:
                    resp = httpx.post(
                        _TRANSCRIBER_URL,
                        files={"file": ("audio.mp3", f, "audio/mpeg")},
                        data={"language": language or "", "timestamps": "false"},
                        timeout=180,
                    )
                resp.raise_for_status()
                result = resp.json()
                transcript = result.get("text")
                detected_language = result.get("language")
                logger.info(
                    "baael_transcribe: transcribed %d chars for %s",
                    len(transcript or ""), url,
                )
            except Exception as e:
                logger.warning("baael_transcribe: transcriber call failed for %s: %s", url, e)

    except Exception as e:
        logger.warning("baael_transcribe: audio download failed for %s: %s", url, e)
        try:
            ydl_opts = {"quiet": True, "skip_download": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                meta = _extract_meta(info)
        except Exception as e2:
            return {"ok": False, "error": f"No se pudo procesar la URL: {e2}"}

    return {
        "ok": True,
        **meta,
        "transcript": transcript,
        "language": detected_language,
    }
