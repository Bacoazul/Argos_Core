## Project_Map

```bash
python ~/.claude/scripts/project_context.py Argos_Core
# → 2 bugs activos (latencia + warmup), router CHAT/AGENT, dependencias
```

Wiki: `.claude/project_map/01-Projects/Argos_Core.md` — router heurístico, stack, fixes conocidos.

---

## MCP Server (2026-06-06)

Argos monta un servidor MCP en `:8000/mcp` (streamable-http) para clientes externos
(Claude Desktop, ollmcp). **Capa separada de `ARGOS_TOOLS`** (las tools internas del
LangGraph). 7 tools en `core/mcp_*.py`, instancia en `core/mcp_server.py`, montaje en
`api.py` (`http_app` + `combine_lifespans`). Modelo por rol en `model_config.json`
(`core/config.py`). Clientes: `MCP_CLIENTS.md`.

- Deps nuevas van en `requirements.txt` (Dockerfile instala de ahí, NO de pyproject):
  `uv pip compile pyproject.toml --python-version 3.12 --python-platform linux -o requirements.txt`
- Cada redeploy bota las sesiones MCP (en memoria) → reconectar cliente.
- `amon_lights`: off/on/color/brillo hacen `/amon/stop` antes (escena activa pisa el comando).

## graphify

Knowledge graph en `graphify-out/`.

- Antes de responder arquitectura/codebase → leer `graphify-out/GRAPH_REPORT.md`
- Si existe `graphify-out/wiki/index.md` → navegar wiki en vez de leer archivos raw
- Tras modificar código → `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"`
