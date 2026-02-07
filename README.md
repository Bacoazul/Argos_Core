# 👁️ ARGOS CORE - Sovereign AI Agent

> "My primary constraint is zero reliance on cloud APIs—every solution must be fully local."

Argos is a local-first, autonomous AI agent engineered to run on consumer hardware (NVIDIA RTX 5090). It utilizes **LangGraph** for orchestration, **Ollama** for inference, and **Docker** for secure execution.

## 🏗️ Architecture

* **Brain:** Qwen2.5-Coder (via Ollama) running on Host GPU.
* **Body:** Python 3.12 + LangGraph running in Docker Container.
* **Memory:** Persistent state management via Checkpointers.
* **Hands:** File System Access (Read/Write/List) inside sandbox.

## 🚀 Quick Start

### Prerequisites
* Windows 11 with NVIDIA GPU (RTX 3090/4090/5090 recommended).
* [Docker Desktop](https://www.docker.com/) installed.
* [Ollama](https://ollama.com/) running locally.

### Installation

1.  **Clone the repository:**
    \\\ash
    git clone https://github.com/YOUR_USERNAME/Argos_Core.git
    cd argos_core
    \\\

2.  **Build the Containment Unit:**
    \\\ash
    docker build -t argos-core:v1 .
    \\\

3.  **Ignite the Agent:**
    \\\ash
    docker run -it --rm \
      --name argos_instance \
      --add-host=host.docker.internal:host-gateway \
      -e OLLAMA_BASE_URL="http://host.docker.internal:11434" \
      argos-core:v1
    \\\

## 🛡️ Security
Argos runs inside a **non-root Docker container**. File system operations are restricted to the container's ephemeral storage unless volumes are explicitly mounted.

## 🗺️ Roadmap
- [x] Phase 1: Local Inference Setup
- [x] Phase 2: Logic Core (Qwen3)
- [x] Phase 3: Orchestration (LangGraph)
- [x] Phase 4: Tools (File System)
- [x] Phase 5: Docker Isolation
- [ ] Phase 6: External Memory (RAG)
