"""
Production-ready logging utilities for ATX.

This module provides:
- structured JSON file logging
- regex-based filtering
- safe root logger attachment
- multi-worker Gunicorn compatibility
- SSE-friendly log file tailing support
"""

import os
import re
import json
import logging
from datetime import datetime


class RegexFilter(logging.Filter):
    """
    Logging filter that excludes records matching a regex pattern.
    """

    def __init__(self, pattern=None):
        super().__init__()
        self.pattern = re.compile(pattern) if pattern else None

    def filter(self, record):
        if not self.pattern:
            return True
        return not bool(self.pattern.search(record.getMessage()))


class JsonFormatter(logging.Formatter):
    """
    Formats log records as JSON lines for easy SSE streaming and frontend parsing.
    """

    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "levelname": record.levelname,
            "module": record.module,
            "message": record.getMessage()
        }

        return json.dumps(log_entry, ensure_ascii=False)


class StreamLogger:
    """
    Production-safe logger wrapper for file-based logging.

    Designed for:
    - Flask apps
    - Gunicorn multi-worker deployments
    - SSE log tail streaming
    """

    def __init__(
        self,
        name="atx_logger",
        level=logging.INFO,
        filter_regex=None,
        log_file=None
    ):
        self.name = name
        self.level = level
        self.log_file = log_file

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        # Avoid duplicate handlers on reload / multiple imports
        if not self.logger.handlers:
            self._setup_handler(filter_regex)

    def _setup_handler(self, filter_regex=None):
        """
        Creates and attaches file handler.
        """
        if not self.log_file:
            raise ValueError("log_file path is required")

        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        file_handler = logging.FileHandler(
            self.log_file,
            mode="a",
            encoding="utf-8"
        )

        file_handler.setLevel(self.level)
        file_handler.setFormatter(JsonFormatter())

        if filter_regex:
            file_handler.addFilter(RegexFilter(filter_regex))

        self.logger.addHandler(file_handler)

    def attach_root(self):
        """
        Safely attach this logger's handlers to root logger.

        Prevents duplicate handler registration.
        """
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)

        existing_handler_types = {
            type(handler) for handler in root_logger.handlers
        }

        for handler in self.logger.handlers:
            if type(handler) not in existing_handler_types:
                root_logger.addHandler(handler)

    def get_logger(self):
        """
        Returns underlying Python logger instance.
        """
        return self.logger

    def get_log_file(self):
        """
        Returns log file path.
        """
        return self.log_file

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def debug(self, message):
        self.logger.debug(message)

    def critical(self, message):
        self.logger.critical(message)