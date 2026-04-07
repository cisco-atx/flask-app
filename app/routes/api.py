import datetime
import hashlib
import importlib
import json
import logging
import os
import shutil
import sys
import tempfile

from flask import Blueprint, request, jsonify, session, current_app, send_from_directory, abort, make_response


def update_profile():
    """ Updates the profile information for the currently logged-in user. """
    username = session.get("username")
    if not username:
        return jsonify(success=False, message="No user logged in"), 401

    user_data = current_app.users_db.get(username, {})

    user_data["firstname"] = request.form.get("firstname", user_data.get("firstname"))
    user_data["lastname"] = request.form.get("lastname", user_data.get("lastname"))
    user_data["email"] = request.form.get("email", user_data.get("email"))

    password = request.form.get("password")
    if password:
        user_data["password"] = hashlib.sha256(password.encode()).hexdigest()

    current_app.users_db.update({username: user_data})

    return jsonify(success=True)


def get_user_connectors():
    """ Retrieves the connectors logged-in user. """
    username = session.get("username")
    if not username:
        return jsonify(success=False, message="No user logged in"), 401

    connector_json = os.path.join(session["userdata"]["home_dir"], "connector.json")
    if not os.path.exists(connector_json):
        return jsonify({})
    connector_data = json.loads(open(connector_json, "r").read())
    for name, data in connector_data.items():
        for field in ["jumphost_password", "network_password"]:
            if field in data:
                data[field] = current_app.cipher.decrypt(data[field])
    return jsonify(success=True, connectors=connector_data)


def save_user_connector():
    """ Saves or updates the Connector configuration for the currently logged-in user. """
    username = session.get("username")
    if not username:
        return jsonify(success=False, message="No user logged in"), 401
    payload = request.get_json()
    name = payload.get("name")
    data = payload.get("data", {})

    for field in ["jumphost_password", "network_password"]:
        data[field] = current_app.cipher.encrypt(data[field])

    connector_json = os.path.join(session["userdata"]["home_dir"], "connector.json")
    connector_data = open(connector_json, "r").read() if os.path.exists(connector_json) else "{}"
    connector_data = json.loads(connector_data)
    connector_data[name] = data
    with open(connector_json, "w") as f:
        json.dump(connector_data, f, indent=4)

    return jsonify(success=True)


def delete_user_connector():
    """ Deletes a specific Connector configuration for the currently logged-in user. """
    username = session.get("username")
    if not username:
        return jsonify(success=False, message="No user logged in"), 401
    payload = request.get_json()
    name = payload.get("name")

    connector_json = os.path.join(session["userdata"]["home_dir"], "connector.json")
    if not os.path.exists(connector_json):
        return jsonify(success=False, message="Connector configuration not found"), 404
    connector_data = json.loads(open(connector_json, "r").read())
    if name not in connector_data:
        return jsonify(success=False, message="Connector configuration not found"), 404
    del connector_data[name]
    with open(connector_json, "w") as f:
        json.dump(connector_data, f, indent=4)

    return jsonify(success=True)


def get_users():
    """ Retrieves a list of all registered users. """
    return jsonify(success=True, users=dict(current_app.users_db))


def add_user():
    """ Register a new admin user with the provided username and password. """
    payload = request.get_json()
    current_app.auth.register(
        **{
            "username": payload.get("username"),
            "password": payload.get("password"),
            "role": payload.get("role"),
            "firstname": payload.get("firstname"),
            "lastname": payload.get("lastname"),
            "email": payload.get("email"),
        }
    )

    return jsonify(success=True)


def change_user_role():
    """ Changes the role of a specified user. """
    payload = request.get_json()
    username = payload.get("username")
    new_role = payload.get("role")

    if not username or not new_role:
        return jsonify(success=False, message="Username and role are required"), 400

    user_data = current_app.users_db.get(username)
    if not user_data:
        return jsonify(success=False, message="User not found"), 404

    user_data["meta"]["role"] = new_role
    current_app.users_db.update({username: user_data})

    return jsonify(success=True)


def update_user_theme():
    """ Updates the theme preference for a specified user. """
    payload = request.get_json()
    username = payload.get("username")
    new_theme = payload.get("theme")

    if not username or not new_theme:
        return jsonify(success=False, message="Username and theme are required"), 400

    user_data = current_app.users_db.get(username)
    if not user_data:
        return jsonify(success=False, message="User not found"), 404

    user_data["theme"] = new_theme
    current_app.users_db.update({username: user_data})
    session["userdata"]["theme"] = new_theme

    return jsonify(success=True)


def delete_user():
    """ Deletes a specified user from the system. """
    payload = request.get_json()
    username = payload.get("username")

    if not username:
        return jsonify(success=False, message="Username is required"), 400

    if username not in current_app.users_db:
        return jsonify(success=False, message="User not found"), 404

    del current_app.users_db[username]

    # Delete user dir
    user_dir = os.path.join(current_app.utils.USERS_DIR, username)
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)

    return jsonify(success=True)


def load_blueprints():
    """ Scans the blueprints directory for valid blueprints, registers them with the application, and returns their metadata. """
    bps = {}
    for bp_id in os.listdir(current_app.utils.BP_DIR):
        bp_path = os.path.join(current_app.utils.BP_DIR, bp_id)

        if not os.path.isdir(bp_path):
            continue

        init_py = os.path.join(bp_path, "__init__.py")
        if not os.path.exists(init_py):
            continue

        try:
            spec = importlib.util.spec_from_file_location(
                f"blueprints.{bp_id}",
                init_py,
                submodule_search_locations=[bp_path]
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            bp_cls = getattr(module, "BP_CLASS", None)

            if not bp_cls:
                logging.warning(f"Blueprint {bp_id} does not define BP_CLASS, skipping")
                continue

            try:
                _validate_bp_class(bp_cls)
            except Exception as e:
                logging.warning(f"Blueprint {bp_id} contract validation failed: {e}, skipping")
                continue

            bps[bp_id] = {
                "id": bp_id,
                "path": bp_path,
                **getattr(bp_cls, "meta", {}),
            }

            if bp_id not in current_app.blueprints:
                current_app.register_blueprint(bp_cls())

        except Exception as e:
            logging.warning(f"Failed to load blueprint {bp_id}: {e}, skipping")

    return jsonify(bps)


def get_blueprint_icon(blueprint_id):
    """ Retrieves the icon file for a specified blueprint. """
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
    """ Handles the upload of a new blueprint as a zip file, extracts it to the blueprints directory, and registers it."""
    files = request.files.getlist("files")

    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    bp_dir = current_app.utils.BP_DIR

    first_file = files[0]
    root_dir = first_file.filename.split("/", 1)[0]
    target_dir = os.path.join(bp_dir, root_dir)

    if os.path.exists(target_dir):
        return jsonify({"error": "Script already exists"}), 400

    os.makedirs(target_dir, exist_ok=True)

    for file in files:
        rel_path = file.filename
        full_path = os.path.join(bp_dir, rel_path)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        file.save(full_path)

    try:
        load_blueprints()
    except Exception as e:
        shutil.rmtree(target_dir)
        return jsonify({"error": f"Failed to load blueprint: {e}"}), 500

    return jsonify({"status": "ok"})


def delete_blueprint():
    """ Deletes a specified blueprint from the system. """
    payload = request.get_json()
    keys_to_delete = payload.get("keys", [])
    deleted = []

    for key in keys_to_delete:
        app_path = os.path.join(current_app.utils.BP_DIR, key)
        if os.path.exists(app_path):
            try:
                shutil.rmtree(app_path)
                deleted.append(key)
            except Exception as e:
                return jsonify(error=str(e)), 500
        deleted.append(key)
    return jsonify(deleted=deleted)


def _validate_bp_class(bp_cls):
    """ Validates that the provided blueprint class adheres to the required contract for blueprints in the application. """
    if not issubclass(bp_cls, Blueprint):
        raise ValueError("BP_CLASS must be a subclass of Blueprint")

    meta = getattr(bp_cls, "meta", None)
    if not isinstance(meta, dict):
        raise ValueError("BP_CLASS must have a 'meta' dictionary attribute")

    for field in ["name", "description", "version"]:
        if field not in meta:
            raise ValueError(f"BP_CLASS meta must include '{field}' field")


def get_reports(path=None):
    """ Retrieves a list of available reports for the currently logged-in user, optionally filtered by a specified subdirectory path. """
    reports_dir = session["userdata"]["reports_dir"]

    if path:
        reports_dir = os.path.join(reports_dir, path)

    if not reports_dir or not os.path.exists(reports_dir):
        return jsonify([])

    files = []
    for f in os.listdir(reports_dir):
        path = os.path.join(reports_dir, f)
        if os.path.isfile(path):
            created = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
            files.append({
                "filename": f,
                "created": created
            })

    # Sort by most recent first
    files.sort(key=lambda x: x["created"], reverse=True)
    return jsonify(files)


def download_report(filename, path=None):
    """ Allows the currently logged-in user to download a specific report file, optionally from a specified subdirectory path. """
    reports_dir = session["userdata"]["reports_dir"]

    if path:
        reports_dir = os.path.join(reports_dir, path)

    if not reports_dir or not os.path.exists(reports_dir):
        abort(404)
    try:
        return send_from_directory(reports_dir, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)


def delete_report(filename, path=None):
    """ Allows the currently logged-in user to delete a specific report file, optionally from a specified subdirectory path. """
    reports_dir = session["userdata"]["reports_dir"]

    if path:
        reports_dir = os.path.join(reports_dir, path)

    if not reports_dir or not os.path.exists(reports_dir):
        return jsonify(success=False, message="Reports directory not found"), 404

    filepath = os.path.join(reports_dir, filename)

    # Security: prevent directory traversal
    if not os.path.abspath(filepath).startswith(os.path.abspath(reports_dir)):
        return jsonify(success=False, message="Invalid file path"), 400

    if not os.path.exists(filepath):
        return jsonify(success=False, message="File not found"), 404

    try:
        os.remove(filepath)
        return jsonify(success=True, message=f"{filename} deleted successfully")
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500


def render_html():
    """ Renders an HTML file from a specified path, ensuring that the file is located within the temporary directory for security reasons. """
    file_path = request.args.get("path")
    if not file_path:
        abort(404)

    tmp_dir = tempfile.gettempdir()
    if not os.path.abspath(file_path).startswith(os.path.abspath(tmp_dir)):
        abort(403)

    if not os.path.exists(file_path):
        abort(404)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        response = make_response(content)
        response.headers["Content-Type"] = "text/html"
        return response
    except Exception as e:
        abort(500)
