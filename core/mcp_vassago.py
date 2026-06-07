"""
MCP tool: vassago_search — búsqueda en los 27k planos industriales (DuckDB).

Subagente Vassago. DB montada ro en /projects/vassago. Búsqueda full-text por
palabras (todas deben aparecer) sobre search_text. Para identificadores exactos
NO se usa LIKE con comodines — eso queda para una tool aparte si se necesita.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import duckdb

from core.mcp_server import mcp
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

# Path dentro del contenedor (vol ro). Override por env para dev local.
_DB_PATH = os.getenv(
    "VASSAGO_DB_PATH",
    "/projects/vassago/data/staging/staging_index.duckdb",
)
_MAX_RESULTS = 50


def _harden(text: str) -> str:
    """Normaliza igual que el buscador cliente: minúsculas, solo alfanumérico."""
    normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", normalized).strip()


@mcp.tool
def vassago_search(query: str, top_n: int = 10) -> dict[str, Any]:
    """
    Busca planos industriales en el índice documental de Vassago (27k+ planos).
    Búsqueda por palabras: todas las palabras del query deben aparecer en el
    contenido/metadatos del plano. Devuelve hasta top_n coincidencias con su
    código de plano, nombre, descripción, categoría y zona de fábrica.

    Úsalo para: encontrar planos por tema, equipo, sistema o zona. Ejemplos:
    vassago_search("bomba centrifuga area 200"), vassago_search("tablero electrico").
    """
    words = _harden(query).split()
    if not words:
        return {"ok": False, "error": "query vacío tras normalizar", "results": []}

    top_n = max(1, min(_MAX_RESULTS, top_n))

    if not Path(_DB_PATH).exists():
        return {"ok": False, "error": f"DB no encontrada: {_DB_PATH}", "results": []}

    conditions = " AND ".join(["search_text LIKE ?"] * len(words))
    params = [f"%{w}%" for w in words]

    try:
        con = duckdb.connect(_DB_PATH, read_only=True)
        try:
            rows = con.execute(
                f"""
                SELECT filename, name, description, category, factory_zone
                FROM blueprints_staging
                WHERE {conditions}
                ORDER BY filename
                LIMIT ?
                """,
                [*params, top_n],
            ).fetchall()
        finally:
            con.close()
    except Exception as e:
        logger.error("vassago_search falló: %s", e)
        return {"ok": False, "error": str(e), "results": []}

    results = [
        {
            "plano": Path(r[0]).stem,
            "nombre": r[1] or "",
            "descripcion": r[2] or "",
            "categoria": r[3] or "",
            "zona": r[4] or "",
        }
        for r in rows
    ]
    return {"ok": True, "count": len(results), "results": results}
