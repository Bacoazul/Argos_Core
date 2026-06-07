# SESSIONS — Argos Core

## 2026-06-07

### Implementado
- **Validadas las 3 tools MCP pendientes** contra backend vivo: `decarabia_analyze` (gemma4), `anima_generate` (wake ComfyUI), `frigate_cam` (list+snapshot).
- **Plan Jarvis Fase A**: el agente LangGraph hereda las 7 manos MCP. Adaptador único `core/mcp_langchain_adapter.py` (FunctionTool→StructuredTool, DRY). `ARGOS_TOOLS` 7→14; `prompts.py` describe las manos; `agent.py` suma keywords de router (luz/cámara/foto/imagen).
- **Migración del path AGENT a llama-server (Qwen3.6-35B-A3B, GGUF Unsloth UD-Q4_K_M)**: ~180 tok/s, tool-calling confiable (single+parallel) vs qwen3-coder-next que desbordaba VRAM. `config.py` `agent_backend` (ollama|openai); `agent.py` `_build_agent_llm()` → `ChatOpenAI` con `extra_body chat_template_kwargs enable_thinking=false`. dep `langchain-openai`. Query prod end-to-end ~2s.
- **Convivencia VRAM resuelta con `llama-swap`** (`C:\tools\llama-swap\`): carga el agente on-demand, descarga tras TTL 600s → libera ~24.5GB para visión gemma4. Verificado 24973→3413 MiB. Autostart `Startup\startup-jarvis.vbs`.
- **Fix bug luces**: `/amon/control` (bridge) detiene el runner antes de aplicar comando manual → escena→color/brillo ya no se pisa. Cubre dashboard/app/Telegram/MCP.
- **Docs**: CLAUDE.md (raíz), Project Map (Argos_Core.md), sección ayuda del dashboard (arquitectura). Memorias actualizadas.

### Pendiente
- **Reboot test** (autostart de llama-swap al login) — diferido por Chucho.
- **Router**: agregar keywords `plano`/`planos` — queries vassago en lenguaje natural caen a CHAT (0.8b) y alucinan sin llamar la tool.
- Solapamiento agente+visión en la MISMA query → gemma4 va a CPU (lento, no crashea); escalar a "stack llama-swap completo" solo si molesta.
- Plan Jarvis: Fase B (estado human-readable, ya emergente con qwen3.6) + voz en app Flutter.
- **Rotar secretos** (GITHUB_TOKEN, PAT GitHub, `.env` en Project_Map/raw) — pendiente de antes.

### Decisiones técnicas
- Agente en llama.cpp/llama-swap, NO Ollama (qwen3-coder-next 79B desbordaba 32GB→CPU). Backend conmutable en `model_config.json` (rollback fácil a ollama).
- Reusar el GGUF de Ollama fue imposible (variante visión `qwen35moe` incompatible con llama.cpp estándar) → GGUF texto de Unsloth.
- `llama-swap` (TTL) elegido sobre encoger a IQ3 o migrar todo a llama.cpp: libera VRAM al ecosistema cuando el agente está idle, sin perder calidad.
- Fix de luces en el bridge (no en cada cliente) → una sola corrección cubre todos los frontends.
- El fallo de tool-calling de qwen3.6 era del motor/template de Ollama, no del modelo (funciona con llama-server `--jinja`).

### Problemas
- **Deploy no se disparaba**: pushear `Argos_Core` NO despliega; el workflow `Deploy Asmodeus` vive en el repo **Asmodeus** y dispara con push ahí o `gh workflow run`. Corregido.
- Scheduled Task sin admin (Access Denied) → solución user-space, luego reemplazada por llama-swap.
- PS5.1 rompe `.ps1` con UTF-8 sin BOM (acentos/em-dash) → solo ASCII.
- `llama-swap` usa flags estilo Go (un guion): `-config`/`-listen`.
- `chat_template_kwargs` va en `extra_body`, no `model_kwargs`, para `ChatOpenAI`.

---

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
