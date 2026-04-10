import json
import os
import time
from flask import current_app, render_template, Response, stream_with_context

def render_home():
    """ Renders the home page for logged-in users."""
    return render_template("atx.home.html")

def activity():
    """ Streams the global log file as Server-Sent Events (SSE) for real-time activity monitoring."""
    log_file = current_app.global_logger.get_log_file()

    def event_stream():
        with open(log_file, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)

            while True:
                line = f.readline()

                if not line:
                    time.sleep(0.5)
                    continue

                yield f"data: {line.strip()}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )