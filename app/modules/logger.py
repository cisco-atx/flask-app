"""
app/modules/logger.py

Summary: Custom logging utilities with regex-based filtering and file
stream support.

Description:
    This module defines `RegexFilter` for excluding log records based on
    a regular expression and `StreamLogger`, a custom logger that writes
    formatted log records to a file and can attach its handlers to the
    root logger.
"""

import logging
import os
import re


class RegexFilter(logging.Filter):
    """Filter that excludes log records matching a regex pattern."""

    def __init__(self, pattern=None):
        """Initialize with an optional regex pattern."""
        super().__init__()
        self.pattern = re.compile(pattern) if pattern else None

    def filter(self, record):
        """Return True if the record does not match the pattern."""
        if not self.pattern:
            return True
        return not self.pattern.search(repr(record))


class StreamLogger(logging.Logger):
    """Logger that writes JSON-formatted records to a file."""

    def __init__(
            self, name, log_file, level=logging.INFO,
            filter_regex=None
    ):
        """Initialize logger with file output and optional filtering."""
        super().__init__(name, level)
        self.log_file = log_file
        self.level = level
        self.filter_regex = filter_regex

        self.propagate = False
        self.formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(module)s | %(message)s",
                                           datefmt="%Y-%m-%d %H:%M:%S")
        if not self.handlers:
            self._setup_file_handler()

    def _setup_file_handler(self):
        """Configure and attach a file handler to this logger."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        file_handler = logging.FileHandler(self.log_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(self.formatter)

        if self.filter_regex:
            file_handler.addFilter(RegexFilter(self.filter_regex))

        self.addHandler(file_handler)

    def attach_root(self):
        """Attach this logger's handlers to the root logger."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)

        existing_handler_types = {
            type(handler) for handler in root_logger.handlers
        }
        # Avoid adding duplicate handler types to root logger
        for handler in self.handlers:
            if type(handler) not in existing_handler_types:
                root_logger.addHandler(handler)
