"""
app/routes/base.py

Summary: Flask views for rendering the home page and streaming log
activity.

Description:
    This module provides route handlers for rendering the application
    home page and streaming the global application log as
    Server-Sent Events (SSE) for real-time activity monitoring.
"""

# Standard library imports
import json
import logging
import os
import time

# Third-party imports
from flask import (
    Response,
    current_app,
    render_template,
    stream_with_context,
)


def render_home():
    """Render the home page for logged-in users."""
    return render_template("atx.home.html")

def activity():
    """Stream the global application log file as Server-Sent Events (SSE)."""
    log_file = current_app.global_logger.log_file

    def log_event():
        # Send last 500 lines as history
        with open(log_file, "r", encoding="utf-8") as f:
            history = f.readlines()[-500:]

        for line in history:
            line = _parse_log_line(line)
            if line:
                yield f"data: {line}\n\n"

        # Start tailing from EOF for live updates
        with open(log_file, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)

            while True:
                line = _parse_log_line(f.readline())
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    # heartbeat keeps connection alive
                    yield ": keep-alive\n\n"
                    time.sleep(1)

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
    try:
        parts = line.strip().split(" | ")
        return json.dumps({
            "asctime": parts[0],
            "levelname": parts[1],
            "module": parts[2],
            "message": " | ".join(parts[3:]),
        })
    except Exception:
        return None
