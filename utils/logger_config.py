"""
Argos Core - Structured Logging Configuration Module

This module provides a JSON-based structured logging system for the Argos Core project.
It implements dual output (file + console) with exception handling and ISO 8601 timestamps.

English Code Rule: All code, comments, and documentation in English.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class ArgosStructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format for structured ingestion.
    
    Each log entry includes:
    - timestamp: ISO 8601 format UTC timestamp
    - level: Log severity level (INFO, WARNING, ERROR, etc.)
    - module: Source module name
    - message: The actual log message
    - exception: Stack trace (if applicable)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),  # RFC 3339 compliant
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # Include exception information if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Include extra fields if provided
        if hasattr(record, 'extra_fields'):
            log_record.update(record.extra_fields)
        
        return json.dumps(log_record, ensure_ascii=False)


def setup_argos_logging(
    log_level: int = logging.INFO,
    log_file: str = "argos_system.log",
    enable_console: bool = True,
    enable_file: bool = True
) -> logging.Logger:
    """
    Initialize and configure the Argos Core logging system.
    
    Args:
        log_level: Minimum logging level (default: INFO)
        log_file: Path to the log file (default: argos_system.log)
        enable_console: Enable console output (default: True)
        enable_file: Enable file output (default: True)
        
    Returns:
        Configured logger instance for argos_core
        
    Raises:
        IOError: If log file cannot be created or written to
    """
    logger = logging.getLogger("argos_core")
    logger.setLevel(log_level)
    
    # Prevent duplicate handlers if called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()
    
    formatter = ArgosStructuredFormatter()
    
    # Console Handler for real-time monitoring
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)
    
    # File Handler for persistent audit logs
    if enable_file:
        try:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            # If file logging fails, log to console and continue
            if enable_console:
                logger.error(f"Failed to initialize file logging: {e}")
            else:
                raise
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_argos_logger() -> logging.Logger:
    """
    Get the configured Argos logger instance.
    
    Returns:
        The argos_core logger (initializes if not already configured)
    """
    logger = logging.getLogger("argos_core")
    
    # Initialize if not already configured
    if not logger.hasHandlers():
        setup_argos_logging()
    
    return logger


if __name__ == "__main__":
    # Initialize the logging system
    argos_logger = setup_argos_logging()
    
    # Demonstration of different log levels
    argos_logger.info("Argos logging system initialized under Phase 1 protocol.")
    argos_logger.debug("Debug mode active - detailed diagnostics enabled.")
    argos_logger.warning("This is a warning message for demonstration purposes.")
    
    # Demonstrate exception logging
    try:
        result = 10 / 0
    except ZeroDivisionError:
        argos_logger.exception("Mathematical error encountered during initialization test.")
    
    argos_logger.info("Logger configuration test completed successfully.")
