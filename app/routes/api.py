"""API routes for user, connectors, blueprints, and reports.

This module defines Flask route handlers for managing users,
connectors, blueprints, and report files. It includes operations
such as CRUD actions, file handling, and blueprint registration.
Logging is added for critical operations and failures.

File path: app/routes/api.py
"""

import datetime
import hashlib
import importlib
import json
import logging
import os
import pkgutil
import shutil
import sys
import tempfile

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    make_response,
    request,
    send_from_directory,
    session,
)

logger = logging.getLogger(__name__)


def update_profile():
    """Update the profile information for the logged-in user."""
    username = session.get("username")
    if not username:
        return jsonify(success=False, message="No user logged in"), 401

    user_data = current_app.users_db.get(username, {})

    user_data["firstname"] = request.form.get(
        "firstname", user_data.get("firstname")
    )
    user_data["lastname"] = request.form.get(
        "lastname", user_data.get("lastname")
    )
    user_data["email"] = request.form.get(
        "email", user_data.get("email")
    )

    password = request.form.get("password")
    if password:
        user_data["password"] = hashlib.sha256(
            password.encode()
        ).hexdigest()

    current_app.users_db.update({username: user_data})

    return jsonify(success=True)


def get_user_connectors():
    """Retrieve connectors for the logged-in user."""
    username = session.get("username")
    if not username:
        return jsonify(success=False, message="No user logged in"), 401

    connector_json = os.path.join(
        session["userdata"]["home_dir"], "connector.json"
    )

    if not os.path.exists(connector_json):
        return jsonify({})

    with open(connector_json, "r") as f:
        connector_data = json.load(f)

    for data in connector_data.values():
        for field in ["jumphost_password", "network_password"]:
            if field in data:
                data[field] = current_app.cipher.decrypt(data[field])

    return jsonify(success=True, connectors=connector_data)


def save_user_connector():
    """Save or update a connector configuration for the user."""
    username = session.get("username")
    if not username:
        return jsonify(success=False, message="No user logged in"), 401

    payload = request.get_json()
    name = payload.get("name")
    data = payload.get("data", {})

    for field in ["jumphost_password", "network_password"]:
        if field in data:
            data[field] = current_app.cipher.encrypt(data[field])

    connector_json = os.path.join(
        session["userdata"]["home_dir"], "connector.json"
    )

    if os.path.exists(connector_json):
        with open(connector_json, "r") as f:
            connector_data = json.load(f)
    else:
        connector_data = {}

    connector_data[name] = data

    with open(connector_json, "w") as f:
        json.dump(connector_data, f, indent=4)

    return jsonify(success=True)


def delete_user_connector():
    """Delete a connector configuration for the user."""
    username = session.get("username")
    if not username:
        return jsonify(success=False, message="No user logged in"), 401

    payload = request.get_json()
    name = payload.get("name")

    connector_json = os.path.join(
        session["userdata"]["home_dir"], "connector.json"
    )

    if not os.path.exists(connector_json):
        return (
            jsonify(
                success=False,
                message="Connector configuration not found",
            ),
            404,
        )

    with open(connector_json, "r") as f:
        connector_data = json.load(f)

    if name not in connector_data:
        return (
            jsonify(
                success=False,
                message="Connector configuration not found",
            ),
            404,
        )

    del connector_data[name]

    with open(connector_json, "w") as f:
        json.dump(connector_data, f, indent=4)

    return jsonify(success=True)


def get_users():
    """Retrieve all registered users."""
    return jsonify(success=True, users=dict(current_app.users_db))


def add_user():
    """Register a new admin user."""
    payload = request.get_json()

    current_app.auth.register(
        **{
            "username": payload.get("username"),
            "password": payload.get("password"),
            "role": payload.get("role"),
            "profile": {
                "firstname": payload.get("firstname"),
                "lastname": payload.get("lastname"),
                "email": payload.get("email"),
            },
        }
    )

    return jsonify(success=True)


def change_user_role():
    """Change the role of a user."""
    payload = request.get_json()
    username = payload.get("username")
    new_role = payload.get("role")

    if not username or not new_role:
        return (
            jsonify(
                success=False,
                message="Username and role are required",
            ),
            400,
        )

    user_data = current_app.users_db.get(username)
    if not user_data:
        return jsonify(success=False, message="User not found"), 404

    user_data["meta"]["role"] = new_role
    current_app.users_db.update({username: user_data})

    return jsonify(success=True)


def update_user_theme():
    """Update the theme preference for a user."""
    payload = request.get_json()
    username = payload.get("username")
    new_theme = payload.get("theme")

    if not username or not new_theme:
        return (
            jsonify(
                success=False,
                message="Username and theme are required",
            ),
            400,
        )

    user_data = current_app.users_db.get(username)
    if not user_data:
        return jsonify(success=False, message="User not found"), 404

    user_data["theme"] = new_theme
    current_app.users_db.update({username: user_data})
    session["userdata"]["theme"] = new_theme

    return jsonify(success=True)


def delete_user():
    """Delete a user from the system."""
    payload = request.get_json()
    username = payload.get("username")

    if not username:
        return jsonify(success=False, message="Username is required"), 400

    if username not in current_app.users_db:
        return jsonify(success=False, message="User not found"), 404

    del current_app.users_db[username]

    user_dir = os.path.join(current_app.utils.USERS_DIR, username)
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)

    return jsonify(success=True)


def load_blueprints():
    """Scan, validate, and register blueprints."""
    bps = {}
    bp_dir = current_app.utils.BP_DIR
    base_dir = os.path.dirname(bp_dir)

    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    for module_info in pkgutil.iter_modules([bp_dir]):
        if not module_info.ispkg:
            continue

        bp_id = module_info.name
        bp_path = os.path.join(bp_dir, bp_id)

        try:
            module = importlib.import_module(f"blueprints.{bp_id}")
            bp_cls = getattr(module, "BP_CLASS", None)

            if not bp_cls:
                logger.warning(
                    "Blueprint %s missing BP_CLASS", bp_id
                )
                continue

            try:
                _validate_bp_class(bp_cls)
            except Exception as exc:
                logger.warning(
                    "Blueprint validation failed: %s (%s)",
                    bp_id,
                    exc,
                )
                continue

            bp = {
                "id": bp_id,
                "path": bp_path,
                **getattr(bp_cls, "meta", {}),
            }

            bp_instance = bp_cls()

            if not current_app._got_first_request:
                try:
                    current_app.register_blueprint(bp_instance)
                    logger.info("Blueprint registered: %s", bp_id)
                except Exception as exc:
                    logger.error(
                        "Failed to register blueprint %s: %s",
                        bp_id,
                        exc,
                    )

            bp["is_registered"] = (
                    current_app.blueprints.get(bp_instance.name)
                    is not None
            )
            bps[bp_id] = bp

        except Exception as exc:
            logger.warning(
                "Failed to load blueprint %s: %s", bp_id, exc
            )

    current_app.bp_db.clear()
    current_app.bp_db.update(bps)

    return jsonify(bps)


def get_blueprint_icon(blueprint_id):
    """Retrieve the icon for a blueprint."""
    bp = current_app.bp_db.get(blueprint_id)
    if not bp:
        return jsonify(success=False, message="Blueprint not found"), 404

    icon_path = os.path.join(bp["path"], bp["icon"])

    if not os.path.exists(icon_path):
        return jsonify(success=False, message="Icon not found"), 404

    with open(icon_path, "rb") as f:
        icon_data = f.read()

    return icon_data, 200, {"Content-Type": "image/png"}


def upload_blueprint():
    """Upload and register a new blueprint."""
    files = request.files.getlist("files")

    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    bp_dir = current_app.utils.BP_DIR
    root_dir = files[0].filename.split("/", 1)[0]
    target_dir = os.path.join(bp_dir, root_dir)

    if os.path.exists(target_dir):
        return jsonify({"error": "Script already exists"}), 400

    os.makedirs(target_dir, exist_ok=True)

    for file in files:
        full_path = os.path.join(bp_dir, file.filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        file.save(full_path)

    try:
        load_blueprints()
    except Exception as exc:
        shutil.rmtree(target_dir)
        logger.exception("Blueprint upload failed")
        return (
            jsonify({"error": f"Failed to load blueprint: {exc}"}),
            500,
        )

    logger.info("Blueprint uploaded: %s", root_dir)
    return jsonify({"status": "ok"})


def delete_blueprint():
    """Delete specified blueprints."""
    payload = request.get_json()
    keys_to_delete = payload.get("keys", [])
    deleted = []

    for key in keys_to_delete:
        app_path = os.path.join(current_app.utils.BP_DIR, key)
        if os.path.exists(app_path):
            try:
                shutil.rmtree(app_path)
                logger.info("Blueprint deleted: %s", key)
            except Exception as exc:
                logger.exception("Failed to delete blueprint: %s", key)
                return jsonify(error=str(exc)), 500
        deleted.append(key)

    return jsonify(deleted=deleted)


def _validate_bp_class(bp_cls):
    """Validate blueprint class contract."""
    if not issubclass(bp_cls, Blueprint):
        raise ValueError("BP_CLASS must be a subclass of Blueprint")

    meta = getattr(bp_cls, "meta", None)
    if not isinstance(meta, dict):
        raise ValueError("BP_CLASS must have a 'meta' dictionary")

    for field in ["name", "description", "version"]:
        if field not in meta:
            raise ValueError(f"Missing meta field: {field}")


def get_reports(path=None):
    """Retrieve report files for the user."""
    reports_dir = session["userdata"]["reports_dir"]

    if path:
        reports_dir = os.path.join(reports_dir, path)

    if not reports_dir or not os.path.exists(reports_dir):
        return jsonify([])

    files = []
    for f_name in os.listdir(reports_dir):
        file_path = os.path.join(reports_dir, f_name)
        if os.path.isfile(file_path):
            created = datetime.datetime.fromtimestamp(
                os.path.getmtime(file_path)
            ).strftime("%Y-%m-%d %H:%M:%S")
            files.append({"filename": f_name, "created": created})

    files.sort(key=lambda x: x["created"], reverse=True)
    return jsonify(files)


def download_report(filename, path=None):
    """Download a report file."""
    reports_dir = session["userdata"]["reports_dir"]

    if path:
        reports_dir = os.path.join(reports_dir, path)

    if not reports_dir or not os.path.exists(reports_dir):
        abort(404)

    try:
        return send_from_directory(
            reports_dir, filename, as_attachment=True
        )
    except FileNotFoundError:
        abort(404)


def delete_report(filename, path=None):
    """Delete a report file."""
    reports_dir = session["userdata"]["reports_dir"]

    if path:
        reports_dir = os.path.join(reports_dir, path)

    if not reports_dir or not os.path.exists(reports_dir):
        return (
            jsonify(
                success=False,
                message="Reports directory not found",
            ),
            404,
        )

    filepath = os.path.join(reports_dir, filename)

    if not os.path.abspath(filepath).startswith(
            os.path.abspath(reports_dir)
    ):
        return jsonify(success=False, message="Invalid file path"), 400

    if not os.path.exists(filepath):
        return jsonify(success=False, message="File not found"), 404

    try:
        os.remove(filepath)
        return jsonify(
            success=True,
            message=f"{filename} deleted successfully",
        )
    except Exception as exc:
        return jsonify(success=False, message=str(exc)), 500


def render_html():
    """Render an HTML file from a temporary directory."""
    file_path = request.args.get("path")
    if not file_path:
        abort(404)

    tmp_dir = tempfile.gettempdir()
    if not os.path.abspath(file_path).startswith(
            os.path.abspath(tmp_dir)
    ):
        abort(403)

    if not os.path.exists(file_path):
        abort(404)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        response = make_response(content)
        response.headers["Content-Type"] = "text/html"
        return response
    except Exception:
        logger.exception("Failed to render HTML")
        abort(500)
