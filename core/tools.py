"""
Argos Core - Tools Module
Phase 8: GitHub Integration (Audited, Secure & Type-Safe)
"""
import os
import functools
from typing import Optional, Literal
from langchain_core.tools import tool
from ddgs import DDGS
from github import Github, Auth
from github.GithubException import GithubException

# --- CONFIGURACIÓN DE LÍMITES (Seguridad) ---
MAX_FILE_BYTES = 512 * 1024  # 512 KB
MAX_ISSUE_TITLE_CHARS = 256
MAX_ISSUE_BODY_CHARS = 8000

# --- FILE SYSTEM TOOLS ---
@tool
def list_files(directory: str) -> str:
    """Lists files in a local directory."""
    try:
        files = os.listdir(directory)
        return f"Files in '{directory}': {files}"
    except Exception as e:
        return f"Error listing files: {e}"

@tool
def read_file(file_path: str) -> str:
    """Reads a local file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(file_path: str, content: str) -> str:
    """Writes to a local file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to '{file_path}'."
    except Exception as e:
        return f"Error writing file: {e}"

# --- INTERNET TOOL ---
@tool
def web_search(query: str) -> str:
    """Searches the internet using DuckDuckGo."""
    print(f"\n[DEBUG] Searching web for: {query}...")
    try:
        raw_results = list(DDGS().text(query, max_results=3))
        if not raw_results:
            return "No results found."

        formatted_results = []
        for r in raw_results:
            entry = f"Title: {r.get('title')}\nLink: {r.get('href')}\nSnippet: {r.get('body')}"
            formatted_results.append(entry)
        return "\n---\n".join(formatted_results)
    except Exception as e:
        return f"Internet search failed: {e}"

# --- GITHUB TOOLS ---
@functools.lru_cache(maxsize=1)
def _get_github_client() -> Github:
    """Crea la conexión con GitHub una sola vez (Cache)."""
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN no está configurado.")
    return Github(auth=Auth.Token(token))

def _safe_github_error(e: GithubException) -> str:
    """Traduce errores de GitHub a mensajes seguros para el LLM."""
    status = getattr(e, "status", None)
    if status in (401, 403):
        return "GITHUB_ERROR: Permisos insuficientes o token inválido (401/403)."
    if status == 404:
        return "GITHUB_ERROR: No encontré el repositorio o el archivo (404)."
    if status == 422:
        return "GITHUB_ERROR: Parámetros inválidos para la operación (422)."
    return f"GITHUB_ERROR: Error de API (Código {status})."

@tool
def github_manager(
    action: Literal["list_repos", "read_file", "create_issue"],
    repo_name: Optional[str] = None,
    file_path: Optional[str] = None,
    issue_title: Optional[str] = None,
    issue_body: Optional[str] = None,
) -> str:
    """
    Herramienta para interactuar con GitHub.
    - 'list_repos': Lista repositorios.
    - 'read_file': Lee archivo. Requiere 'repo_name' y 'file_path'.
    - 'create_issue': Crea issue. Requiere 'repo_name' e 'issue_title'.
    """
    try:
        g = _get_github_client()
    except RuntimeError as e:
        return f"GITHUB_TOOL_ERROR: {e}"

    try:
        if action == "list_repos":
            repos = g.get_user().get_repos()
            repo_list = [r.full_name for r in repos][:15]
            return "Repositorios disponibles:\n" + "\n".join(repo_list)

        if action == "read_file":
            if not repo_name or not file_path:
                return "GITHUB_TOOL_ERROR: Faltan argumentos 'repo_name' o 'file_path'."
            
            file_path = os.path.normpath(file_path).lstrip('/')
            if file_path.startswith('..') or file_path == '.':
                return "GITHUB_TOOL_ERROR: Ruta de archivo inválida."
            
            repo = g.get_repo(repo_name)
            content = repo.get_contents(file_path)
            
            # FIX: PyGithub devuelve una lista si la ruta es un directorio
            if isinstance(content, list):
                return "GITHUB_TOOL_ERROR: La ruta apunta a un directorio, no a un archivo. Por favor, especifica un archivo concreto."
            
            if getattr(content, "size", 0) > MAX_FILE_BYTES:
                return "GITHUB_TOOL_ERROR: El archivo supera el límite de lectura (512 KB)."
            
            decoded = content.decoded_content.decode("utf-8", errors="replace")
            return f"--- Contenido de {file_path} ---\n{decoded}"

        if action == "create_issue":
            if not repo_name or not issue_title:
                return "GITHUB_TOOL_ERROR: Faltan argumentos 'repo_name' o 'issue_title'."
            
            title = issue_title.strip()[:MAX_ISSUE_TITLE_CHARS]
            body = (issue_body or "Creado automáticamente por Argos Core.").strip()
            if len(body) > MAX_ISSUE_BODY_CHARS:
                body = body[:MAX_ISSUE_BODY_CHARS] + "\n\n[Truncado por límite interno]."
            
            repo = g.get_repo(repo_name)
            issue = repo.create_issue(title=title, body=body)
            return f"Éxito: Issue creado en {issue.html_url}"

        return "GITHUB_TOOL_ERROR: Acción no reconocida."

    except GithubException as e:
        return _safe_github_error(e)
    except Exception as e:
        return f"GITHUB_TOOL_ERROR: Error interno: {type(e).__name__}"

# --- LISTA MAESTRA DE HERRAMIENTAS ---
ARGOS_TOOLS = [list_files, read_file, write_file, web_search, github_manager]