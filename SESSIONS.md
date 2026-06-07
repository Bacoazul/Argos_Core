# SESSIONS — Argos Core

## 2026-06-06

### Implementado
- **Servidor MCP sobre Argos Core**: FastMCP montado en `:8000/mcp` (streamable-http) vía `combine_lifespans`, sin tocar rutas REST. 7 tools: `get_datetime`, `amon_lights`, `vassago_search`, `project_map`, `decarabia_analyze`, `anima_generate`, `frigate_cam`.
- `model_config.json` + `core/config.py`: modelo por rol (agent/chat/vision/embed), fallback a env; cableado en `agent.py` + `api.py`.
- `core/bridge_client.py` (cliente Windows Bridge autónomo); `requirements.txt` regenerado con fastmcp+duckdb (Linux).
- Compose: `argos-core` expone `8000:8000`; Frigate creds en `.env`. **Desplegado vía CI/CD y verificado en producción.**
- **Claude Desktop conectado** vía `mcp-remote` (config en caja MSIX). Validado end-to-end (búsqueda de planos + huella en logs).
- Fix `amon_lights`: `/amon/stop` antes de control manual + endpoint `/amon/scene` correcto + action `stop`.
- Resumen de contenido (`_Asmodeus/.env` `OLLAMA_MODEL`) → `gemma4:26b` (evita overflow VRAM).
- Docs: CLAUDE.md (×3), HANDOFF, _CONTEXT, MCP_CLIENTS.md; Project Map regenerado (Argos_Build, _Asmodeus); 4 memorias nuevas.

### Pendiente
- Validar contra backend vivo: `decarabia_analyze`, `anima_generate`, `frigate_cam`.
- **Plan Jarvis**: dar las 7 manos a Argos como tools LangGraph (dashboard/app las heredan) + voz en app Flutter + tools que reporten estado real (respuestas humanas).
- Modelo agente sigue en `qwen3-coder-next` (desborda VRAM, lento en agent-mode); `qwen3.5:9b` sin probar.
- Qwen local soberano (ollmcp no corre en Windows nativo → WSL2 o GUI).
- **Rotar secretos expuestos**: `GITHUB_TOKEN` (.env Argos), GitHub PAT (config Claude Desktop), `.env` filtrado en `Project_Map/raw/`.

### Decisiones técnicas
- `decarabia_analyze` usa gemma4 por Ollama directo (no workflow ComfyUI) por robustez.
- Tools MCP no importan `_Asmodeus` (replican patrón HTTP) → Argos autónomo.
- MCP montado en `/mcp` (no `/`) para no tapar las rutas REST.
- `qwen3.6:35b` probado como agente: cabe en VRAM pero falla tool-calling → revertido a coder.
- Reparto de modelos: resumen → `gemma4:26b` (alta frecuencia, rápido); agente → `qwen3-coder-next` (confiable con tools).

### Problemas
- Deploy falló 2× : `requirements.txt` no tenía fastmcp (Dockerfile usa requirements, no pyproject); luego `pywin32` (compilado en Windows). Fix: `uv pip compile --python-platform linux`.
- "Apaga las luces" no apagaba: la escena `pulso` pisaba el comando → parar runner antes.
- Link de YouTube "colgado": era `qwen3-coder-next` (53GB) desbordando la GPU de 32GB → mitad en CPU, lentísimo (no estaba colgado).
- Cada redeploy/restart de Argos bota las sesiones MCP → reconectar Claude Desktop.
- `qwen3.6:35b` no llama tools de forma confiable.

---
