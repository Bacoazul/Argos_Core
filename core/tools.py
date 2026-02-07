"""
Argos Core - Tools Module
Phase 7: Internet & File System
"""
import os
from langchain_core.tools import tool
from duckduckgo_search import DDGS

# --- HERRAMIENTAS DE SISTEMA DE ARCHIVOS (Ya las tenías) ---
@tool
def list_files(directory: str) -> str:
    """Lists files in a directory. Use this to explore the file system."""
    try:
        files = os.listdir(directory)
        return f"Files in '{directory}': {files}"
    except Exception as e:
        return f"Error listing files: {e}"

@tool
def read_file(file_path: str) -> str:
    """Reads the content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(file_path: str, content: str) -> str:
    """Writes content to a file. OVERWRITES existing content."""
    try:
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to '{file_path}'."
    except Exception as e:
        return f"Error writing file: {e}"

# --- NUEVA HERRAMIENTA: INTERNET (SENTIDOS) ---
@tool
def web_search(query: str) -> str:
    """
    Searches the internet using DuckDuckGo.
    Use this to find documentation, libraries, or real-world facts.
    """
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            return "No results found."
        return str(results)
    except Exception as e:
        return f"Internet search failed: {e}"

# Lista maestra de herramientas
ARGOS_TOOLS = [list_files, read_file, write_file, web_search]