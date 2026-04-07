import json
from flask import current_app, render_template, Response

def render_home():
    """ Renders the home page for logged-in users."""
    return render_template("atx.home.html")

def activity():
    """ Provides a server-sent events stream of the user's activity log. """
    log_queue = current_app.global_logger.get_queue()
    history = current_app.global_logger.get_history()
    def event_stream():
        for log_entry in history:
            yield f"data: {json.dumps(log_entry)}\n\n"
        while True:
            log_entry = log_queue.get()
            yield f"data: {json.dumps(log_entry)}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")