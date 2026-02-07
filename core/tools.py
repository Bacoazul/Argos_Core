"""
Argos Core - Tools Module
Phase 7: Internet Fix (Formatted & Eager Loading)
"""
import os
from langchain_core.tools import tool
from ddgs import DDGS

# --- FILE SYSTEM TOOLS ---
@tool
def list_files(directory: str) -> str:
    """Lists files in a directory."""
    try:
        files = os.listdir(directory)
        return f"Files in '{directory}': {files}"
    except Exception as e:
        return f"Error listing files: {e}"

@tool
def read_file(file_path: str) -> str:
    """Reads a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(file_path: str, content: str) -> str:
    """Writes to a file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to '{file_path}'."
    except Exception as e:
        return f"Error writing file: {e}"

# --- INTERNET TOOL (MEJORADA) ---
@tool
def web_search(query: str) -> str:
    """
    Searches the internet using DuckDuckGo.
    Returns a formatted summary of the top 3 results.
    """
    print(f"\n[DEBUG] Searching web for: {query}...")
    try:
        # 1. Eager Loading (Evita el Hang)
        raw_results = list(DDGS().text(query, max_results=3))
        
        if not raw_results:
            return "No results found."

        # 2. Parsing (Mejora la legibilidad para el Agente)
        formatted_results = []
        for r in raw_results:
            title = r.get('title', 'No Title')
            link = r.get('href', 'No Link')
            body = r.get('body', 'No Content')
            entry = f"Title: {title}\nLink: {link}\nSnippet: {body}"
            formatted_results.append(entry)

        return "\n---\n".join(formatted_results)

    except Exception as e:
        return f"Internet search failed: {e}"

ARGOS_TOOLS = [list_files, read_file, write_file, web_search]