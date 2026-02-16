"""
Logging configuration for Intelligent Memory System
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logging(
    log_dir: str = None,
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """
    Setup logging for the application.

    Args:
        log_dir: Directory to store log files
        log_level: Logging level (default: INFO)
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        max_bytes: Max bytes per log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Root logger instance
    """
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        log_dir = os.path.abspath(log_dir)

    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if log_to_file:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"memory_system_{today}.log")

        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return root_logger


if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Logging system initialized")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
