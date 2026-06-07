"""
Argos Core - Adaptador MCP → LangChain.

Plan Jarvis (Fase A): las 7 "manos" del servidor MCP (capa para clientes externos)
se exponen TAMBIÉN al agente LangGraph interno (ARGOS_TOOLS), sin duplicar lógica.

`@mcp.tool` deja en el namespace del módulo la FUNCIÓN original (callable directo);
el FunctionTool vive aparte en el registro de FastMCP. Aquí cada función se envuelve
en un `StructuredTool` de LangChain — nombre, descripción y esquema de argumentos los
infiere LangChain del `__name__`, `__doc__` y type hints de la firma. `frigate_cam`
es async → se pasa como `coroutine`; el agente ya corre 100% async (`ainvoke` +
`ToolNode` async), así que encaja nativo.

Fuente única: si mañana se agrega una tool MCP nueva y se añade aquí, el agente la
hereda sin tocar `agent.py`.
"""
from __future__ import annotations

import inspect
from typing import Any

from langchain_core.tools import StructuredTool

from core import (
    mcp_comfyui,
    mcp_frigate,
    mcp_projectmap,
    mcp_tools,
    mcp_vassago,
    mcp_vision,
)
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

# Las 7 funciones decoradas con @mcp.tool (el nombre de módulo sigue siendo la función).
_MCP_FUNCTION_TOOLS: list[Any] = [
    mcp_tools.get_datetime,
    mcp_tools.amon_lights,
    mcp_vassago.vassago_search,
    mcp_projectmap.project_map,
    mcp_vision.decarabia_analyze,
    mcp_comfyui.anima_generate,
    mcp_frigate.frigate_cam,
]


def _to_langchain(fn: Any) -> StructuredTool:
    """Envuelve una función @mcp.tool en un StructuredTool de LangChain."""
    name = fn.__name__
    description = (fn.__doc__ or name).strip()
    if inspect.iscoroutinefunction(fn):
        return StructuredTool.from_function(coroutine=fn, name=name, description=description)
    return StructuredTool.from_function(func=fn, name=name, description=description)


def build_mcp_langchain_tools() -> list[StructuredTool]:
    """Devuelve las 7 manos MCP como tools LangChain. Nunca lanza por una sola tool."""
    out: list[StructuredTool] = []
    for t in _MCP_FUNCTION_TOOLS:
        try:
            out.append(_to_langchain(t))
        except Exception as ex:  # una tool malformada no debe tumbar el agente
            logger.error("No se pudo adaptar tool MCP %r a LangChain: %s", getattr(t, "name", t), ex)
    logger.info("MCP→LangChain: %d/%d manos heredadas por el agente", len(out), len(_MCP_FUNCTION_TOOLS))
    return out


MCP_AS_LANGCHAIN: list[StructuredTool] = build_mcp_langchain_tools()
