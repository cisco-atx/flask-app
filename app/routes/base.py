"""
Flask base routes for home page and activity streaming and notification management

This module defines route handlers responsible for rendering the
application home page and streaming application log activity using
Server-Sent Events (SSE). It enables real-time monitoring by tailing
the log file and pushing updates to connected clients.

Provides CRUD for admin-managed announcement/maintenance notifications
that are surfaced as dismissible banners on the home page.

Path: app/routes/base.py
"""

import json
import logging
import os
import time
import datetime
import uuid

from flask import Response, current_app, render_template, stream_with_context, jsonify, request

logger = logging.getLogger(__name__)

# Notification types allowed. Mapped to badge styling on the frontend.
VALID_TYPES = {"info", "warning", "maintenance", "critical"}


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

def get_notifications():
    """Return active notifications visible to the current session."""
    db = current_app.notifications_db
    now = datetime.datetime.now()

    active = []
    for nid, note in db.items():
        if not note.get("enabled", True):
            continue

        expires_at = note.get("expires_at")
        if expires_at:
            try:
                if datetime.datetime.fromisoformat(expires_at) < now:
                    continue
            except ValueError:
                logger.warning("Bad expires_at on notification %s", nid)

        # Ensure id is present in the payload for client dismissal tracking.
        active.append({**note, "id": nid})

    active.sort(key=lambda n: n.get("priority", 0), reverse=True)
    return jsonify({"success": True, "notifications": active})


def list_notifications():
    """Return all notifications (admin view, includes disabled/expired)."""
    db = current_app.notifications_db
    items = [{**note, "id": nid} for nid, note in db.items()]
    items.sort(key=lambda n: n.get("priority", 0), reverse=True)
    return jsonify({"success": True, "notifications": items})


def save_notification():
    """Create or update a notification (admin only)."""
    data = request.get_json(silent=True) or {}

    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "message": "Message is required"}), 400

    ntype = data.get("type", "info")
    if ntype not in VALID_TYPES:
        return jsonify({"success": False, "message": "Invalid type"}), 400

    db = current_app.notifications_db
    nid = data.get("id") or str(uuid.uuid4())

    record = {
        "type": ntype,
        "title": (data.get("title") or "").strip(),
        "message": message,
        "priority": int(data.get("priority") or 0),
        "persistent": bool(data.get("persistent", False)),
        "enabled": bool(data.get("enabled", True)),
        "expires_at": (data.get("expires_at") or "").strip() or None,
        "updated_at": datetime.datetime.now().isoformat(),
    }

    db[nid] = record
    logger.info("Saved notification %s", nid)
    return jsonify({"success": True, "id": nid})


def delete_notification():
    """Delete a notification by id (admin only)."""
    data = request.get_json(silent=True) or {}
    nid = data.get("id")

    db = current_app.notifications_db
    if nid in db:
        del db[nid]
        logger.info("Deleted notification %s", nid)
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Not found"}), 404