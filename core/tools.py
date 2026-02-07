"""
Argos Core - Tools Module
Defines the "Hands" of the agent: File System & Code Execution capabilities.
"""
import os
from langchain_core.tools import tool
from typing import List
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

# --- FILE SYSTEM TOOLS ---

@tool
def list_files(directory: str = ".") -> str:
    """
    List files in a directory. 
    Use this to see what files exist before reading or writing.
    Args:
        directory: The relative path (default is current folder '.').
    """
    try:
        files = os.listdir(directory)
        # Filter hidden files/directories
        visible_files = [f for f in files if not f.startswith('.')]
        logger.info(f"Tool used: list_files('{directory}')")
        return f"Files in '{directory}': {visible_files}"
    except Exception as e:
        return f"Error listing files: {str(e)}"

@tool
def read_file(file_path: str) -> str:
    """
    Read the contents of a file.
    Use this to analyze code before editing it.
    Args:
        file_path: The path to the file (e.g., 'main.py').
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Tool used: read_file('{file_path}')")
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def write_file(file_path: str, content: str) -> str:
    """
    Write content to a file. 
    WARNING: This overwrites existing files. Always verify path first.
    Args:
        file_path: The target file path.
        content: The full code or text to write.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Tool used: write_file('{file_path}')")
        return f"Successfully wrote to '{file_path}'."
    except Exception as e:
        return f"Error writing file: {str(e)}"

# Registry of available tools
ARGOS_TOOLS = [list_files, read_file, write_file]