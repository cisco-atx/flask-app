"""
Flask base routes for home page and activity streaming.

This module defines route handlers responsible for rendering the
application home page and streaming application log activity using
Server-Sent Events (SSE). It enables real-time monitoring by tailing
the log file and pushing updates to connected clients.

Path: app/routes/base.py
"""

import json
import logging
import os
import time

from flask import Response, current_app, render_template, stream_with_context

logger = logging.getLogger(__name__)


def render_home():
    """Render the home page for logged-in users."""
    return render_template("atx.home.html")


def activity():
    """Stream the global application log file as SSE."""
    log_file = current_app.global_logger.log_file

    def log_event():
        """Generate log events for SSE stream."""
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                history = f.readlines()[-500:]
        except Exception:
            logger.exception("Failed to read log file for history")
            return

        for line in history:
            parsed_line = _parse_log_line(line)
            if parsed_line:
                yield f"data: {parsed_line}\n\n"

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                f.seek(0, os.SEEK_END)

                while True:
                    line = f.readline()
                    parsed_line = _parse_log_line(line)

                    if parsed_line:
                        yield f"data: {parsed_line.strip()}\n\n"
                    else:
                        # Heartbeat to keep connection alive
                        yield ": keep-alive\n\n"
                        time.sleep(1)
        except Exception:
            logger.exception("Error while streaming log file")

    return Response(
        stream_with_context(log_event()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _parse_log_line(line):
    """Parse a log line into JSON format for SSE transmission."""
    try:
        parts = line.strip().split(" | ")
        if len(parts) < 4:
            return None

        return json.dumps(
            {
                "asctime": parts[0],
                "levelname": parts[1],
                "module": parts[2],
                "message": " | ".join(parts[3:]),
            }
        )
    except Exception:
        logger.exception("Failed to parse log line")
        return None
