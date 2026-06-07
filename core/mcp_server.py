"""
Argos Core - MCP server.

Instancia FastMCP del ecosistema Asmodeus. Se monta sobre el FastAPI de api.py
como sub-app ASGI (streamable-http). Las tools viven en core.mcp_tools y se
registran al importarse al final de este módulo.
"""
from __future__ import annotations

from fastmcp import FastMCP

mcp: FastMCP = FastMCP("Asmodeus Ecosystem")

# Registrar las tools (cada módulo usa @mcp.tool contra la instancia de arriba).
# Import al final para evitar import circular (cada módulo importa este).
from core import mcp_tools       # noqa: E402,F401  get_datetime, amon_lights
from core import mcp_vassago     # noqa: E402,F401  vassago_search
from core import mcp_projectmap  # noqa: E402,F401  project_map
from core import mcp_vision      # noqa: E402,F401  decarabia_analyze
from core import mcp_comfyui     # noqa: E402,F401  anima_generate
from core import mcp_frigate     # noqa: E402,F401  frigate_cam
