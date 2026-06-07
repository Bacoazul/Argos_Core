# Briefing — Latencia del agente Argos (para investigación externa)

> Objetivo: que un asistente con acceso a internet investigue cómo **acelerar la
> inferencia del modelo agente** manteniendo **tool-calling confiable** y **100% local**
> (stack soberano, sin APIs de nube).

## Hardware
- GPU: **NVIDIA RTX 5090, 32 GB VRAM** (Legion T7)
- RAM: 64 GB · CPU desktop
- Driver host: 596.49 (CUDA 12.9+, mayo 2026)
- OS: Windows 11; Ollama corre nativo en el host; el agente corre en Docker (WSL2 backend) y llama a Ollama por `host.docker.internal:11434`.

## Stack
- **Ollama** sirve los modelos.
- **Argos Core**: FastAPI + **LangGraph** (grafo agente↔ToolNode, 100% async).
- Cliente LLM: `langchain-ollama` `ChatOllama` con `bind_tools()` (function calling estilo OpenAI).
- Router heurístico: queries simples → modelo chat rápido; queries con tools/razonamiento → modelo AGENT.

## Modelo agente actual
- **`qwen3-coder-next:latest`**
  - Familia `qwen3next` (MoE), **79.7B params**, cuant. **Q4_K_M**
  - Archivo en disco: **~52 GB**
  - `num_ctx` (context): **8192**
  - `keep_alive`: 300 s (5 min)
- En ejecución, Ollama reporta `size_vram ≈ 31 GB` → **no cabe entero en 32 GB**: parte de las capas se descargan a **RAM/CPU** (offload). Resultado: generación de tokens lenta.

## El problema (latencia), dos componentes
1. **Cold start:** la 1ª query AGENT tras estar descargado el modelo debe **cargar ~31 GB a VRAM** (lento, ~1 min). Solo ocurre en frío; con keep_alive caliente, las siguientes no recargan.
2. **Inferencia lenta sostenida:** como el modelo **desborda los 32 GB**, parte vive en CPU → cada token es lento **en toda** query AGENT (no solo la primera). GPU al 99% pero throughput bajo por el offload.

Las **tools en sí son rápidas** (frigate list/snapshot ~instante-2s, visión gemma4 pocos s, generación de imagen anima ~2 min por ser inherente). El cuello de botella es **el LLM agente**, no las tools.

## Restricciones duras
- **Tool-calling confiable es obligatorio** (el agente DEBE emitir tool calls bien formadas; LangGraph las ejecuta).
- **100% local / soberano** — sin Anthropic/OpenAI/etc.
- Preferible mantener Ollama (pero se aceptan alternativas locales: vLLM, llama.cpp, TGI, etc. si justifican el cambio).

## Alternativas ya probadas y DESCARTADAS
- **`qwen3.6:35b`**: cabe en 32 GB (sin offload, sería rápido) pero **falla tool-calling** (no emite/mal-emite las llamadas).
- **`qwen3.5:9b`**: probado, **también falla tool-calling**.
- Conclusión actual: el único tool-caller confiable disponible es `qwen3-coder-next`, que es lento por desbordar VRAM. Tradeoff: rápido-pero-no-llama-tools vs llama-tools-pero-lento.

## Lo que IDEALMENTE necesitamos (preguntas de investigación)
1. **Caber 79.7B en 32 GB sin perder tool-calling:** ¿existe una cuant. más agresiva de qwen3-coder-next (Q3_K_M, IQ3, Q2_K, AWQ, GPTQ) que entre completa en VRAM **sin romper** el function-calling? ¿Cuál es el punto de quiebre calidad/tools?
2. **KV-cache quantization** (Ollama `OLLAMA_KV_CACHE_TYPE=q8_0/q4_0`, flash-attention): ¿cuánta VRAM libera con `num_ctx=8192`? ¿afecta tool-calling?
3. **Tuning de offload:** ¿ajustar `num_gpu` (capas en GPU) / `num_batch` mejora throughput dado el offload parcial inevitable?
4. **Speculative decoding / draft models** en Ollama o vLLM para MoE qwen3next: ¿soportado? ¿ganancia real?
5. **Runtime alternativo:** ¿vLLM / llama.cpp / TGI dan mejor throughput que Ollama para este modelo en una sola RTX 5090, manteniendo function-calling?
6. **Otro modelo local que (a) quepa entero en 32 GB y (b) tenga tool-calling sólido:** candidatos a evaluar en 2026 (p. ej. familias con buen function-calling ~14–32B Q4). ¿Cuáles tienen reputación fiable de tool-calling y caben?
7. **Cold-start:** ¿`keep_alive=-1` permanente para el agente es viable dado que el modelo de visión (gemma4:26b) y chat (0.8b) también compiten por VRAM? ¿Estrategia de swapping?

## Datos para benchmarking (si propone pruebas)
- Comando estado VRAM: `nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv`
- Modelos cargados: `curl http://localhost:11434/api/ps`
- Modelo de visión: `gemma4:26b` · chat: `qwen3.5:0.8b` · embed: `nomic-embed-text` (comparten la misma GPU).

---

## ✅ VALIDACIÓN (2026-06-07) — solución encontrada y probada

**Solución: `qwen3.6:35b-A3B` (GGUF limpio de Unsloth) en `llama-server` con `--jinja`, thinking OFF.**

- **Tool-calling: FUNCIONA** (single y parallel multi-tool, args correctos, sin loops ni fuga de thinking). El fallo previo era del **motor/template de Ollama**, NO del modelo.
- **Velocidad: ~180 tok/s** decode (vs qwen3-coder-next arrastrándose por offload a CPU). ~30-40x.
- **VRAM: 24.5GB / 32GB** (7.6GB libres). Cabe completo, sin offload.
- Hardware validado: llama.cpp b9550 CUDA 13.3 corre nativo en la RTX 5090 (`BLACKWELL_NATIVE_FP4=1`).

**Hallazgo:** el blob de Ollama `qwen3.6:35b` (variante visión, family `qwen35moe`) **NO es compatible con llama.cpp estándar** (`rope.dimension_sections expected 4, got 3`) — Ollama lo corre en su motor Go. Hubo que descargar el GGUF texto de Unsloth (`unsloth/Qwen3.6-35B-A3B-GGUF`, UD-Q4_K_M, 21GB), que sí es llama.cpp-native y trae los fixes de tool-calling.

**Binarios/modelo instalados en:** `C:\tools\llamacpp\` (llama-server b9550 CUDA 13.3) + `C:\tools\llamacpp\models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf`.

**Comando de arranque validado:**
```
llama-server.exe -m models\Qwen3.6-35B-A3B-UD-Q4_K_M.gguf -ngl 99 -c 8192 \
  -fa on -ctk q8_0 -ctv q8_0 --jinja --host 127.0.0.1 --port 8090
```
(En el request: `"chat_template_kwargs":{"enable_thinking":false}`.)

### ✅ INTEGRADO (2026-06-07)
- `core/config.py`: `agent_backend` ("ollama"|"openai") + `agent_base_url`.
- `core/agent.py`: `_build_agent_llm()` — si backend=openai usa `ChatOpenAI` contra llama-server, `extra_body={chat_template_kwargs:{enable_thinking:false}}`. CHAT (0.8b) y visión (gemma4) siguen en Ollama.
- `model_config.json`: backend=openai, `agent_base_url=http://host.docker.internal:8090/v1`, agent="qwen3.6-35b-a3b".
- deps: `langchain-openai` en pyproject + requirements.txt.
- **Launcher host:** `C:\tools\llamacpp\start-jarvis.ps1` (escucha en `0.0.0.0:8090` para que el contenedor lo alcance).
- **Test end-to-end real:** ArgosAgent (backend openai) → llama-server → frigate_cam → tabla markdown, **2.2s**.
- Rollback: poner `agent_backend:"ollama"` en model_config.json + recrear contenedor.

### 🔴 PENDIENTE — convivencia VRAM (próximo)
llama-server persistente acapara 24.5GB → si una query AGENT llama `decarabia_analyze` (gemma4:26b, ~16GB) **no cabe** (24.5+16>32) y la visión fallará/irá a CPU. Falta orquestación **on-demand** (parar llama-server antes de visión / patrón go2rtc vía Windows Bridge). Además: **llama-server debe estar arriba** para el path AGENT — falta auto-start (Startup/Scheduled Task).

*Contexto: Plan Jarvis Fase A (agente LangGraph con 14 tools) ya desplegado; la latencia del modelo agente era el único cuello — ahora resuelta a nivel de runtime, falta integrar.*
