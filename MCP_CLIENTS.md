# Argos MCP — Clientes

El servidor MCP del ecosistema corre montado sobre Argos Core (FastAPI :8000),
endpoint **`/mcp`** (transporte streamable-http). Expone 7 tools.

| Tool | Qué hace |
|---|---|
| `get_datetime` | Fecha/hora real (Colombia UTC-5). Mata alucinación de fecha. |
| `amon_lights` | Luces Govee (on/off/brillo/color/escena/estado) vía Windows Bridge. |
| `vassago_search` | Búsqueda en 27k planos industriales (DuckDB). |
| `project_map` | Estado/rol de cada proyecto del ecosistema (vault Obsidian). |
| `decarabia_analyze` | Análisis multimodal de imágenes (gemma4 visión, local). |
| `anima_generate` | Generación de imágenes anime (Anima/ComfyUI). |
| `frigate_cam` | Cámaras Frigate (list/snapshot/enable/disable). |

URL local: `http://localhost:8000/mcp`
URL Tailscale (otros nodos): `http://100.124.39.87:8000/mcp`

---

## Claude Desktop

Editar `claude_desktop_config.json`:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "asmodeus": {
      "transport": "http",
      "url": "http://100.124.39.87:8000/mcp"
    }
  }
}
```

Reiniciar Claude Desktop. Las 7 tools aparecen en el selector. Probar primero
`get_datetime` y `amon_lights` (sin dependencias pesadas).

---

## Qwen local — ollmcp (NO MCPHost)

> MCPHost está deprecado (sucesor: Kit). Para Ollama usar **ollmcp**
> (`mcp-client-for-ollama`), que soporta streamable-http.

```bash
pip install mcp-client-for-ollama
ollmcp --mcp-server-url http://localhost:8000/mcp --model qwen3-coder-next
```

Alternativa con qwen-code:
```bash
qwen mcp add --transport http asmodeus http://localhost:8000/mcp
```

⚠ Tool-calling fiable: **qwen3-coder-next** sí. `gemma4` no es buena llamando
tools (úsala solo como backend de visión vía `decarabia_analyze`). `qwen3.5:0.8b`
es demasiado chico para orquestar.

---

## Smoke test (curl / python)

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:8000/mcp") as c:
        print([t.name for t in await c.list_tools()])
        print((await c.call_tool("get_datetime", {})).data)

asyncio.run(main())
```
