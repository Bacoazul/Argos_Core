# 👁️ ARGOS CORE

> **The Sovereign AI Workforce.**
> A local-first, dockerized autonomous agent framework built on LangGraph & Ollama.

[![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Status](https://img.shields.io/badge/Status-Phase_7:_Connected-success?style=for-the-badge)](https://github.com/Bacoazul/Argos_Core)

---

## 📖 Overview

**Argos Core** is an open-source initiative to build a truly autonomous "Operating System for AI Agents." Unlike cloud-dependent assistants, Argos runs entirely on your hardware, maintaining strict data sovereignty.

Inspired by the "OpenClaw" philosophy, Argos is designed to live inside a secure **Docker container** while interacting with the outside world through controlled APIs and tools. It serves as a bridge between local LLMs (via Ollama) and real-world actions.

### ⚡ Key Capabilities (Phase 7)

* **🔒 Digital Faraday Cage:** Runs inside a secure Docker environment (`python:3.12-slim`). It cannot accidentally destroy your host OS, but can manipulate its own isolated filesystem.
* **🧠 Neural Link (Local LLM):** Connects to the host machine's Ollama instance via internal Docker networking. No OpenAI API keys required.
* **🌐 Autonomous Internet Access:** Equipped with `ddgs` (DuckDuckGo Search) to perform live web research without tracking or API costs. Handles strict timeout management and eager loading to prevent agent hangs.
* **💾 Persistent Memory:** Utilizes Docker Volume binding to read/write to a local `workspace` folder on the host machine. Information survives container restarts.
* **🛠️ Tool Use:** Capable of executing Python logic to interact with the filesystem and the web dynamically.

---

## 🏗️ Architecture

## 📂 Estructura del Proyecto

```text
Argos_Core
├── 🐳 Dockerfile        # Configuración del contenedor
├── 📦 pyproject.toml    # Dependencias (uv)
├── 📄 README.md         # Documentación
├── 📂 core              # Cerebro del Agente
│   ├── agent.py         # Lógica LangGraph
│   ├── main.py          # Arranque
│   └── tools.py         # Herramientas (Web/Archivos)
└── 📂 workspace         # Memoria (Volumen persistente)
    └── memoria.txt      # Archivos del usuario
```

Argos abandons the traditional "infinite loop" script in favor of a **State Graph** architecture provided by **LangGraph**.

```mermaid
graph LR
    A[User Input] --> B(Router)
    B --> C{Decision}
    C -- Needs Info --> D[Tools Node]
    D -- Web Search / FS Ops --> E[External World]
    E --> D
    D --> F[Agent Node]
    F --> C
    C -- Final Answer --> G[Output]
