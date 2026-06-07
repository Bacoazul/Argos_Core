# HANDOFF — Argos Core
> Última actualización: 2026-06-06
> Pegar en Claude Web o Cowork para continuar con contexto completo.

---

## ⭐ ÚLTIMO CAMBIO — Servidor MCP (2026-06-06)

MCP montado sobre el FastAPI (endpoint `:8000/mcp`, streamable-http) para clientes
externos (Claude Desktop, ollmcp+Qwen, Flutter). Capa separada de `ARGOS_TOOLS`.

- Nuevos: `core/mcp_server.py` (FastMCP) · `core/mcp_{tools,vassago,projectmap,vision,comfyui,frigate}.py` (7 tools) · `core/bridge_client.py` · `core/config.py` (model_config loader) · `model_config.json` · `MCP_CLIENTS.md`
- `api.py`: monta MCP con `combine_lifespans`; `/chat`·`/health`·`/knowledge` intactas
- `agent.py` + `api.py` ahora leen modelo desde `model_config.json` (fallback env)
- deps: `fastmcp` (3.4.2), `duckdb` (1.5.3)
- compose argos-core: `ports: 8000:8000`; Frigate creds en `.env`
- **Desplegado y verificado en producción** (`:8000/mcp`): 7 tools, get_datetime/vassago/project_map/amon_lights OK contra backend vivo
- **Cliente conectado:** Claude Desktop vía `mcp-remote` (config en caja MSIX). ⚠ cada redeploy bota la sesión MCP → reconectar.
- **Fix amon_lights (bbea13f):** off/on/color/brillo hacen `/amon/stop` antes (escena activa pisaba el comando); `scene` usa `/amon/scene {name}`; nueva action `stop`.
- **Fix deploy (6139a4d):** deps en `requirements.txt` (no solo pyproject), regenerar con `uv pip compile --python-platform linux` (sin pywin32).
- **Pendiente validar con backend vivo:** decarabia_analyze, anima_generate, frigate_cam
- Decisión: `decarabia_analyze` usa gemma4 por Ollama directo (no workflow ComfyUI) por robustez
- **Próximo (plan Jarvis):** dar las 7 manos a Argos como tools LangGraph (reutilizar código) → dashboard/app las heredan; voz en app; tools que reporten estado real para respuestas humanas

---

## 1. RESUMEN DEL PROYECTO

Argos Core es el cerebro LLM del ecosistema Asmodeus. FastAPI que expone un agente LangGraph con Ollama como HTTP API. No tiene UI propia — lo consumen Asmodeus (bot Telegram) y el dashboard web (puerto 3001 vía `/api/chat`).

**Estado:** Activo en producción. 2 bugs de performance sin corregir.

---

## 2. STACK Y ESTRUCTURA

```
argos_core/
├── api.py              # FastAPI entry point, lifespan, /chat endpoint, router dual-path
├── core/
│   ├── agent.py        # ArgosAgent: LangGraph StateGraph + dual-path CHAT/AGENT
│   ├── brain.py        # (legacy/wrapper)
│   ├── prompts.py      # System prompts estáticos (CRÍTICO: no poner datetime aquí)
│   ├── tools.py        # ARGOS_TOOLS: 5 tools disponibles para el agent path
│   └── collective.py   # (multi-agent, experimental)
├── utils/
│   └── logger_config.py
└── tests/
```

**Stack:** Python 3.12, FastAPI, LangGraph, AsyncSqliteSaver (checkpoint), langchain-ollama, Docker.

**Modelos:**
- `OLLAMA_MODEL=qwen3-coder-next:latest` → agent path (con tools, ~5-8s)
- `OLLAMA_CHAT_MODEL=qwen3:1.7b` → chat path (sin tools, ~0.5s) — ⚠️ falta en `.env`

**Router heurístico en `agent.py:_is_agent_query()`:** palabras clave → AGENT; todo lo demás → CHAT.

---

## 3. ESTADO ACTUAL

**Hecho:**
- Dual-path router (CHAT ~0.5s / AGENT ~5-8s)
- System prompt estático → prefix cache Ollama
- Fecha en HumanMessage (no invalida cache)
- `ainvoke` + `AsyncSqliteSaver` (no bloquea event loop)
- `recursion_limit=10` (evita tool loops infinitos)
- `_clean_argos_response()` elimina artefactos `Answer:/Rationale:` del modelo

**⚠️ Bugs activos (sin corregir):**

**BUG 1 — Latencia web UI (2026-04-13):**
- `dispatcher_api.py` en Asmodeus pasa `inject_digest=True` al `/chat` de Argos
- El DIGEST contiene la palabra "archivos" → `_is_agent_query()` lo detecta → fuerza AGENT path
- Resultado: chat web tarda ~2 min en lugar de ~0.5s
- **Fix:** en `core/agent.py:_is_agent_query()`, extraer solo la parte después de `[Pregunta del usuario]` antes de evaluar keywords:
```python
# Antes de evaluar keywords, strip el marker de contexto
if "[Pregunta del usuario]" in text:
    text = text.split("[Pregunta del usuario]", 1)[1]
```

**BUG 2 — Warmup (2026-04-13):**
- `qwen3:1.7b` no se precalienta al startup → primera respuesta CHAT tarda ~20s
- **Fix:** en `api.py` lifespan, después de inicializar `_agent`, hacer una request warmup:
```python
# En lifespan, después de _agent = ArgosAgent(memory):
try:
    await _agent.chat("warmup", thread_id="__warmup__")
    logger.info("Chat model warm.")
except Exception:
    pass
```

**Diferido:**
- `OLLAMA_CHAT_MODEL=qwen3:1.7b` falta en `.env` (el fallback funciona pero es implícito)
- Chat path es stateless (no usa LangGraph checkpoint). Solo agent path tiene historial persistente.
- `qwen3:1.7b` falla en aritmética básica — keywords "cuanto es/calcula" redirigen a agent como workaround. Evaluar `qwen3:4b`.

---

## 4. CONTEXTO PARA CLAUDE CHAT

**Para qué usarlo:** debugging de los 2 bugs activos, optimización del router, diseño de nuevas tools.

**Cómo pedirle:**
- "Tengo este bug: `_is_agent_query()` recibe texto que incluye un DIGEST inyectado antes de la pregunta real. Necesito que evalúe keywords solo en la parte del usuario, no en el contexto. Aquí está el código de `agent.py`: [pegar función]. ¿Cuál es el fix mínimo?"
- "Quiero agregar warmup del modelo chat al startup de FastAPI. El lifespan está en `api.py`. Aquí está el código: [pegar lifespan]. ¿Cómo lo hago sin bloquear el startup?"
- "Quiero agregar una nueva tool a ARGOS_TOOLS que [X]. Aquí están las tools actuales: [pegar tools.py]."

---

## 5. ¿ES NECESARIO COWORK?

**No para el desarrollo normal.** Los 2 bugs son cambios quirúrgicos de 2-5 líneas cada uno.

**Potencial futuro:** si se implementa `collective.py` (multi-agent), Cowork podría gestionar el scaffold de agentes paralelos mientras se trabaja en el router. Diferido.

---

## 6. CONTEXTO PARA COWORK

*(no aplica actualmente)*
