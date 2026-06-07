"""
MCP tool: project_map — lee el Project Map (vault Obsidian) del ecosistema.

Vault montado ro en /knowledge/project_map. Sin query devuelve el índice de
proyectos + ECOSYSTEM_SUMMARY. Con query devuelve la nota del proyecto que mejor
coincide, o un keyword-match sobre todas las notas.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.mcp_server import mcp
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

_VAULT = Path(os.getenv("PROJECT_MAP_DIR", "/knowledge/project_map"))
_PROJECTS_DIR = _VAULT / "01-Projects"
_SUMMARY = _VAULT / "ECOSYSTEM_SUMMARY.md"
_MAX_CHARS = 6000


def _list_projects() -> list[str]:
    if not _PROJECTS_DIR.is_dir():
        return []
    return sorted(p.stem for p in _PROJECTS_DIR.glob("*.md"))


def _read_trimmed(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return f"[error leyendo {path.name}: {e}]"
    return text[:_MAX_CHARS] + ("\n[...truncado]" if len(text) > _MAX_CHARS else "")


@mcp.tool
def project_map(query: str | None = None) -> dict[str, Any]:
    """
    Consulta el mapa de proyectos del ecosistema Asmodeus (Project Map, vault
    Obsidian). Es la fuente de verdad del estado, dependencias y rol de cada
    proyecto.

    - Sin query: devuelve la lista de proyectos + el resumen del ecosistema.
    - Con query (ej "Asmodeus", "Argos", "vigilancia"): devuelve la nota del
      proyecto que mejor coincide por nombre, o coincidencias por palabra clave.
    """
    if not _VAULT.is_dir():
        return {"ok": False, "error": f"vault no montado: {_VAULT}"}

    projects = _list_projects()

    if not query:
        summary = _read_trimmed(_SUMMARY) if _SUMMARY.exists() else ""
        return {"ok": True, "projects": projects, "ecosystem_summary": summary}

    q = query.lower().strip()

    # 1) Match por nombre de proyecto (exacto o substring)
    for name in projects:
        if q == name.lower() or q in name.lower():
            return {
                "ok": True,
                "match": name,
                "content": _read_trimmed(_PROJECTS_DIR / f"{name}.md"),
            }

    # 2) Keyword search sobre el cuerpo de las notas
    hits = []
    for name in projects:
        try:
            body = (_PROJECTS_DIR / f"{name}.md").read_text(encoding="utf-8").lower()
        except Exception:
            continue
        if q in body:
            hits.append(name)

    if len(hits) == 1:
        return {
            "ok": True,
            "match": hits[0],
            "content": _read_trimmed(_PROJECTS_DIR / f"{hits[0]}.md"),
        }
    if hits:
        return {"ok": True, "matches": hits, "hint": "varios proyectos coinciden; especifica uno"}

    return {"ok": True, "matches": [], "projects": projects, "hint": "sin coincidencias"}
