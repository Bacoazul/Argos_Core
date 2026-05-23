"""
RAG sobre proyectos de Chucho.

Sources (auto-descubiertas):
  /projects/*/CLAUDE.md, HANDOFF.md, SESSIONS.md
  /knowledge/project_map/*.md

Index: SQLite /data/argos/project_kb.db — sin deps externas.
Embeddings: nomic-embed-text via Ollama HTTP.
Auto-rebuild cuando algún .md fuente es más nuevo que el índice.
"""
import json
import math
import os
import sqlite3
import time
from pathlib import Path

_DB = Path(os.getenv("KNOWLEDGE_DB", "/data/argos/project_kb.db"))
_OLLAMA = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
_EMBED_MODEL = "nomic-embed-text:latest"
_CHUNK_SIZE = 900
_OVERLAP = 150
_TOP_K = 5
_MIN_SCORE = 0.25

_SOURCE_ROOTS: list[tuple[Path, list[str]]] = [
    (Path("/projects"), ["CLAUDE.md", "HANDOFF.md", "SESSIONS.md"]),
    (Path("/knowledge/project_map"), ["*.md"]),
]


# ── Embedding ─────────────────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    import urllib.request
    payload = json.dumps({"model": _EMBED_MODEL, "input": text}).encode()
    req = urllib.request.Request(
        f"{_OLLAMA}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["embeddings"][0]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


# ── Chunking ──────────────────────────────────────────────────────────────────

def _split(text: str, source: str) -> list[tuple[str, str]]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + _CHUNK_SIZE
        chunk = text[start:end].strip()
        if len(chunk) >= 40:
            chunks.append((source, chunk))
        start += _CHUNK_SIZE - _OVERLAP
    return chunks


# ── Source discovery ──────────────────────────────────────────────────────────

def _sources() -> list[Path]:
    files: list[Path] = []
    for base, patterns in _SOURCE_ROOTS:
        if not base.exists():
            continue
        for pat in patterns:
            if "*" in pat:
                files.extend(base.rglob(pat))
            else:
                files.extend(base.rglob(pat))
    return files


# ── DB helpers ────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id       INTEGER PRIMARY KEY,
            source   TEXT,
            content  TEXT,
            embedding TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    return conn


def _built_at(conn: sqlite3.Connection) -> float:
    row = conn.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
    return float(row[0]) if row else 0.0


# ── Stale check ───────────────────────────────────────────────────────────────

def _is_stale() -> bool:
    if not _DB.exists():
        return True
    conn = _connect()
    ts = _built_at(conn)
    conn.close()
    if ts == 0:
        return True
    for f in _sources():
        try:
            if f.stat().st_mtime > ts:
                return True
        except OSError:
            pass
    return False


# ── Rebuild ───────────────────────────────────────────────────────────────────

def rebuild() -> int:
    conn = _connect()
    conn.execute("DELETE FROM chunks")
    total = 0
    for f in _sources():
        try:
            text = f.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue
            for source, chunk in _split(text, str(f)):
                emb = _embed(chunk)
                conn.execute(
                    "INSERT INTO chunks(source, content, embedding) VALUES (?,?,?)",
                    (source, chunk, json.dumps(emb)),
                )
                total += 1
        except Exception:
            continue
    conn.execute("INSERT OR REPLACE INTO meta VALUES ('built_at',?)", (str(time.time()),))
    conn.commit()
    conn.close()
    return total


# ── Query ─────────────────────────────────────────────────────────────────────

def query(text: str, n: int = _TOP_K) -> str:
    """Semantic search. Retorna contexto formateado listo para el LLM."""
    if _is_stale():
        count = rebuild()
        if count == 0:
            return "No hay archivos de proyectos disponibles para consultar."

    q_emb = _embed(text)
    conn = _connect()
    rows = conn.execute("SELECT source, content, embedding FROM chunks").fetchall()
    conn.close()

    scored = sorted(
        ((float(_cosine(q_emb, json.loads(emb))), src, content) for src, content, emb in rows),
        reverse=True,
    )

    top = [r for r in scored[:n] if r[0] >= _MIN_SCORE]
    if not top:
        return "No encontré información relevante sobre ese tema en los proyectos."

    parts = []
    seen_sources: set[str] = set()
    for score, source, content in top:
        label = Path(source).stem
        if label not in seen_sources:
            seen_sources.add(label)
            parts.append(f"[{label}]\n{content.strip()}")
        else:
            parts.append(content.strip())

    return "\n\n---\n\n".join(parts)
