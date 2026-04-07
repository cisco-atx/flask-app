"""
Custom logging utilities for Netaudit.

This module provides a custom logging handler and logger that streams logs via a queue,
with optional file logging and regex-based filtering. It can also capture root logs.

Classes:
- RegexFilter: A logging filter that excludes log records matching a given regex pattern.
- QueueFileHandler: A custom logging handler that sends log records to a queue and optionally writes them to a file.
- StreamLogger: A custom Logger for streaming logs via a queue, with optional file logging and regex-based filtering.
"""

import logging
import re
import queue
import os


class RegexFilter(logging.Filter):
    """
    Logging filter that excludes log records matching a given regex pattern.
    """

    def __init__(self, pattern=None):
        super().__init__()
        self.pattern = re.compile(pattern) if pattern else None

    def filter(self, record):
        if not self.pattern:
            return True
        return bool(not self.pattern.search(repr(record)))


class QueueFileHandler(logging.Handler):
    """
    Custom logging handler that sends log records to a queue and optionally writes them to a file.
    """

    def __init__(self, log_queue, log_file=None, history_limit=1000):
        """
        Initializes the handler.

        Args:
            log_queue (queue.Queue): Queue to send log records to.
            log_file (str, optional): Path to a log file. If provided, logs willalso be written to this file.
            history_limit (int): Maximum number of log records to keep in history.
        """
        super().__init__()
        self.log_queue = log_queue
        self.log_file = log_file
        self.history = []
        self.history_limit = history_limit
        self._file_handle = None

        if self.log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            self._file_handle = open(log_file, "a", encoding="utf-8")

    def emit(self, record):
        """
        Emit a log record.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        try:
            formatted_record = self.format(record) if self.formatter else record.getMessage()
            log_entry = {
                "asctime": getattr(record, "asctime", ""),
                "levelname": record.levelname,
                "module": record.module,
                "message": record.getMessage()
            }

            # Send to queue
            self.log_queue.put(log_entry)

            # Save to history
            self.history.append(log_entry)
            if len(self.history) > self.history_limit:
                self.history.pop(0)

            # Write to file if applicable
            if self._file_handle:
                self._file_handle.write(formatted_record + "\n")
                self._file_handle.flush()

        except Exception:
            self.handleError(record)

    def get_history(self):
        """ Returns the history of log records."""
        return self.history


class StreamLogger(logging.Logger):
    """
    Custom Logger for streaming logs via a queue, with optional file logging
    and regex-based filtering. Can also capture root logs.
    """

    def __init__(self,
                 name,
                 level=logging.INFO,
                 filter_regex=None,
                 log_file=None,
                 history_limit=1000):
        """ Initializes the StreamLogger.

        Args:
            name (str): Name of the logger.
            level (int): Logging level.
            filter_regex (str, optional): Regex pattern to filter out log records.
            log_file (str, optional): Path to a log file. If provided, logs will also be written to this file.
            history_limit (int): Maximum number of log records to keep in history.
        """

        super().__init__(name, level)
        self.level = level
        self.log_queue = queue.Queue()
        self.history_limit = history_limit

        self.handlers.clear()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.queuefile_handler = QueueFileHandler(self.log_queue, log_file, history_limit=history_limit)
        self.queuefile_handler.setFormatter(formatter)

        if filter_regex:
            self.queuefile_handler.addFilter(RegexFilter(filter_regex))

        # Attach handler to this logger
        self.addHandler(self.queuefile_handler)

    def attach_root(self):
        """ Attaches the handler to the root logger."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.level)
        root_logger.addHandler(self.queuefile_handler)

    def get_queue(self):
        """ Returns the log queue."""
        return self.log_queue

    def get_history(self):
        """ Returns the history of log records."""
        return self.queuefile_handler.get_history()
