# 👁️ ARGOS CORE

> **The Sovereign AI Brain.**
> LangGraph agent running locally via Ollama — expuesto como FastAPI para el ecosistema Asmodeus.

[![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Status](https://img.shields.io/badge/Status-Fase_8:_API_Ready-success?style=for-the-badge)](https://github.com/Bacoazul/Argos_Core)

---

## Overview

Argos Core es el cerebro LLM del ecosistema Asmodeus. Corre como contenedor Docker y expone una API HTTP que consume el bot de Telegram (Asmodeus) para todas las consultas de texto libre.

- Sin dependencia de cloud — 100% Ollama local
- Memoria persistente — SQLite checkpointer (LangGraph)
- Tool use — web search (DuckDuckGo), filesystem, GitHub

---

## Arquitectura

```
Asmodeus (bot Telegram)
        |
        v  POST /chat
  +-------------+
  |  FastAPI    |  api.py
  |  ArgosAgent |  core/agent.py  (LangGraph StateGraph)
  |  ChatOllama |  -> host.docker.internal:11434
  +-------------+
        |
    Tools: web_search, list_files, read_file, write_file, github_manager
```

---

## Estructura

```
argos_core/
├── api.py              # FastAPI wrapper — POST /chat, GET /health
├── main.py             # REPL interactivo (desarrollo local)
├── core/
│   ├── agent.py        # ArgosAgent: LangGraph StateGraph + SqliteSaver
│   ├── brain.py        # ArgosBrain: cliente directo Ollama (legado)
│   ├── tools.py        # ARGOS_TOOLS: web_search, filesystem, github_manager
│   └── prompts.py      # System prompt dinamico
├── utils/
│   └── logger_config.py
├── Dockerfile
└── pyproject.toml
```

---

## API

### POST /chat

```json
// Request
{ "message": "que hay en la carpeta /workspace?", "thread_id": "user-123" }

// Response
{ "response": "...", "thread_id": "user-123" }
```

### GET /health

```json
{ "status": "ok", "model": "qwen3-coder:30b" }
```

---

## Stack

| Componente   | Tecnologia                            |
|---|---|
| LLM local    | Ollama — qwen3-coder:30b (default)    |
| Orquestacion | LangGraph (StateGraph + ToolNode)     |
| LLM client   | langchain-ollama (ChatOllama)         |
| Memoria      | langgraph-checkpoint-sqlite           |
| API          | FastAPI + Uvicorn                     |
| Web search   | ddgs (DuckDuckGo)                     |
| GitHub       | PyGithub                              |

---

## Setup

### Variables de entorno (.env)

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3-coder:30b
GITHUB_TOKEN=your_token_here
```

### Levantar via Asmodeus

```bash
cd ../_Asmodeus
docker compose up -d
```

### Levantar standalone

```bash
docker build -t argos-core .
docker run -p 8000:8000 --env-file .env argos-core
```

---

## Modelos compatibles

| Modelo            | Tamano | Notas                                      |
|---|---|---|
| qwen3-coder:30b   | 18GB   | Recomendado — fuerte en codigo y tool use  |
| deepseek-r1:32b   | 19GB   | Excelente reasoning                        |
| qwen3.5:35b-a3b   | 23GB   | MoE — muy rapido                           |
| llama3.3:70b      | 42GB   | Mas potente, requiere mas VRAM             |

---

## Tools disponibles

| Tool                     | Descripcion                           |
|---|---|
| web_search(query)        | DuckDuckGo — 3 resultados, sin API    |
| list_files(directory)    | Lista archivos en directorio local    |
| read_file(file_path)     | Lee archivo (limite 512KB)            |
| write_file(path, content)| Escribe archivo                       |
| github_manager(action)   | list_repos / read_file / create_issue |
