"""
Argos Core - Model config loader.

Fuente única de verdad de qué modelo usa cada rol. Lee model_config.json
(montado como volumen ro), con fallback a las env vars históricas para no
romper el deploy actual. Devuelve un dataclass inmutable (frozen).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from utils.logger_config import get_argos_logger

logger = get_argos_logger()

# Ubicación del JSON. Por defecto junto al código; override por env para Docker.
_CONFIG_PATH = Path(os.getenv("MODEL_CONFIG_PATH", "/projects/argos_core/model_config.json"))


@dataclass(frozen=True)
class ModelConfig:
    """Rol → modelo Ollama. Inmutable."""
    agent: str
    chat: str
    vision: str
    embed: str
    ollama_base_url: str


def _from_env() -> dict:
    """Defaults derivados de las env vars actuales — nunca falla."""
    return {
        "agent": os.getenv("OLLAMA_MODEL", "qwen3-coder-next:latest"),
        "chat": os.getenv("OLLAMA_CHAT_MODEL", "qwen3.5:0.8b"),
        "vision": os.getenv("OLLAMA_VISION_MODEL", "gemma4:26b"),
        "embed": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
    }


@lru_cache(maxsize=1)
def load_model_config() -> ModelConfig:
    """
    Carga model_config.json sobre los defaults de entorno.
    El JSON puede ser parcial — solo las claves presentes hacen override.
    Cualquier error de lectura/parseo cae a env vars (fail-safe).
    """
    data = _from_env()

    if _CONFIG_PATH.exists():
        try:
            raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("model_config.json no es un objeto JSON")
            # Override inmutable: nuevo dict, no mutar 'data' base
            data = {**data, **{k: v for k, v in raw.items() if k in data and v}}
            logger.info("model_config.json cargado: %s", _CONFIG_PATH)
        except Exception as e:
            logger.warning("model_config.json inválido (%s) — usando env vars: %s", _CONFIG_PATH, e)
    else:
        logger.info("model_config.json ausente (%s) — usando env vars", _CONFIG_PATH)

    return ModelConfig(**data)
