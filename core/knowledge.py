"""
RAG sobre proyectos de Chucho.

Sources (auto-descubiertas):
  /projects/*/CLAUDE.md, HANDOFF.md, SESSIONS.md
  /knowledge/project_map/*.md

Index: SQLite WAL /data/argos/project_kb.db — sin deps externas.
Embeddings: nomic-embed-text batch via Ollama HTTP.
Auto-rebuild cuando algún .md es más nuevo que el índice.
Rebuild protegido por threading.Lock — safe para llamadas concurrentes.
"""
import json
import math
import os
import sqlite3
import threading
import time
from pathlib import Path

_DB = Path(os.getenv("KNOWLEDGE_DB", "/data/argos/project_kb.db"))
_OLLAMA = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
_EMBED_MODEL = "nomic-embed-text:latest"
_CHUNK_SIZE = 900
_OVERLAP = 150
_TOP_K = 5
_MIN_SCORE = 0.25
_BATCH_SIZE = 48  # chunks por llamada a Ollama embed

_REBUILD_LOCK = threading.Lock()

_SOURCE_ROOTS: list[tuple[Path, list[str]]] = [
    (Path("/projects"), ["CLAUDE.md", "HANDOFF.md", "SESSIONS.md"]),
    (Path("/knowledge/project_map"), ["*.md"]),
]


# ── Embeddings (batch) ────────────────────────────────────────────────────────

def _embed_batch(texts: list[str]) -> list[list[float]]:
    import urllib.request
    payload = json.dumps({"model": _EMBED_MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        f"{_OLLAMA}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["embeddings"]


def _embed_single(text: str) -> list[float]:
    return _embed_batch([text])[0]


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
        chunk = text[start : start + _CHUNK_SIZE].strip()
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
            files.extend(base.rglob(pat))
    return files


# ── DB helpers ────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id        INTEGER PRIMARY KEY,
            source    TEXT,
            content   TEXT,
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


def _built_at() -> float:
    if not _DB.exists():
        return 0.0
    conn = _connect()
    row = conn.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
    conn.close()
    return float(row[0]) if row else 0.0


# ── Stale check ───────────────────────────────────────────────────────────────

def is_stale() -> bool:
    ts = _built_at()
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
    """Reconstruye el índice. Thread-safe. Retorna cantidad de chunks indexados."""
    with _REBUILD_LOCK:
        # Coletar todos los chunks primero
        all_chunks: list[tuple[str, str]] = []  # (source, text)
        for f in _sources():
            try:
                text = f.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    all_chunks.extend(_split(text, str(f)))
            except Exception:
                continue

        if not all_chunks:
            return 0

        # Batch embeddings — todos los chunks en grupos de _BATCH_SIZE
        sources = [c[0] for c in all_chunks]
        texts = [c[1] for c in all_chunks]
        embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            try:
                embeddings.extend(_embed_batch(batch))
            except Exception:
                embeddings.extend([[] for _ in batch])

        # Escribir a DB
        conn = _connect()
        conn.execute("DELETE FROM chunks")
        for src, content, emb in zip(sources, texts, embeddings):
            if emb:
                conn.execute(
                    "INSERT INTO chunks(source, content, embedding) VALUES (?,?,?)",
                    (src, content, json.dumps(emb)),
                )
        conn.execute(
            "INSERT OR REPLACE INTO meta VALUES ('built_at',?)", (str(time.time()),)
        )
        conn.commit()
        conn.close()
        return len([e for e in embeddings if e])


# ── Query ─────────────────────────────────────────────────────────────────────

def query(text: str, n: int = _TOP_K) -> str:
    """Semantic search. Reconstruye si stale. Retorna contexto formateado."""
    if is_stale():
        count = rebuild()
        if count == 0:
            return "No hay archivos de proyectos disponibles para consultar."

    q_emb = _embed_single(text)
    conn = _connect()
    rows = conn.execute("SELECT source, content, embedding FROM chunks").fetchall()
    conn.close()

    scored = sorted(
        (
            (_cosine(q_emb, json.loads(emb)), src, content)
            for src, content, emb in rows
            if emb and emb != "[]"
        ),
        reverse=True,
    )

    top = [r for r in scored[:n] if r[0] >= _MIN_SCORE]
    if not top:
        return "No encontré información relevante sobre ese tema en los proyectos."

    parts: list[str] = []
    for _, source, content in top:
        label = Path(source).stem
        parts.append(f"[{label}]\n{content.strip()}")

    return "\n\n---\n\n".join(parts)
