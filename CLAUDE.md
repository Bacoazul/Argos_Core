## Project_Map Context

**Quick context without reading code:**
```bash
python ~/.claude/scripts/project_context.py Argos_Core
# → Status, 2 bugs activos (latencia + warmup), dependencias
```

**Wiki article:** `.claude/project_map/01-Projects/Argos_Core.md`
- Router heurístico (CHAT vs AGENT)
- Stack (LangGraph, Ollama, FastAPI)
- Known issues with fixes

**Parent project:** [[Asmodeus]] (consumidor principal)

---

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
