from flask import redirect, url_for

# Importing view functions for rendering pages and handling user activity.
from .base import (
    render_home,
    activity
)

# Importing API views for user profile and connector management.
from .api import (
    update_profile,
    get_user_connectors,
    save_user_connector,
    delete_user_connector,
    get_users,
    add_user,
    change_user_role,
    update_user_theme,
    delete_user,
    load_blueprints,
    get_blueprint_icon,
    upload_blueprint,
    delete_blueprint,
    get_reports,
    download_report,
    delete_report,
    render_html
)

# Importing authentication and authorization views and decorators.
from .login import (
    render_login,
    render_register,
    logout,
    login_required,
    admin_required,
    superadmin_required
)

# Defining the list of routes to be registered with the Flask application.
routes = [
    {
        "rule": "/",
        "endpoint": "atx.redirect_root",
        "view_func": lambda: redirect(url_for("atx.render_home")),
        "methods": ["GET"]
    },
    {
        "rule": "/login",
        "endpoint": "atx.render_login",
        "view_func": render_login,
        "methods": ["GET", "POST"]
    },
    {
        "rule": "/register",
        "endpoint": "atx.render_register",
        "view_func": render_register,
        "methods": ["GET", "POST"]
    },
    {
        "rule": "/logout",
        "endpoint": "atx.redirect_logout",
        "view_func": logout,
        "methods": ["GET"]
    },
    {
        "rule": "/home",
        "endpoint": "atx.render_home",
        "view_func": login_required(render_home),
        "methods": ["GET"]
    },
    {
        "rule": "/activity",
        "endpoint": "atx.sse_activity",
        "view_func": activity,
        "methods": ["GET"]
    },
    {
        "rule": "/api/update_profile",
        "endpoint": "atx.api_update_profile",
        "view_func": login_required(update_profile),
        "methods": ["POST"]
    },
    {
        "rule": "/api/connectors",
        "endpoint": "atx.api_get_user_connectors",
        "view_func": login_required(get_user_connectors),
        "methods": ["GET"]
    },
    {
        "rule": "/api/connector",
        "endpoint": "atx.api_save_user_connector",
        "view_func": login_required(save_user_connector),
        "methods": ["POST"]
    },
    {
        "rule": "/api/connector",
        "endpoint": "atx.api_delete_user_connector",
        "view_func": login_required(delete_user_connector),
        "methods": ["DELETE"]
    },
    {
        "rule": "/api/users",
        "endpoint": "atx.api_get_users",
        "view_func": admin_required(get_users),
        "methods": ["GET"]
    },
    {
        "rule": "/api/user/add",
        "endpoint": "atx.api_add_user",
        "view_func": superadmin_required(add_user),
        "methods": ["POST"]
    },
    {
        "rule": "/api/user/change_role",
        "endpoint": "atx.api_change_user_role",
        "view_func": superadmin_required(change_user_role),
        "methods": ["POST"]
    },
    {
        "rule": "/api/user/update_theme",
        "endpoint": "atx.api_update_user_theme",
        "view_func": login_required(update_user_theme),
        "methods": ["POST"]
    },
    {
        "rule": "/api/user",
        "endpoint": "atx.api_delete_user",
        "view_func": superadmin_required(delete_user),
        "methods": ["DELETE"]
    },
    {
        "rule": "/api/blueprints",
        "endpoint": "atx.api_load_blueprints",
        "view_func": login_required(load_blueprints),
        "methods": ["GET"]
    },
    {
        "rule": "/api/blueprint_icon/<blueprint_id>",
        "endpoint": "atx.api_get_blueprint_icon",
        "view_func": login_required(get_blueprint_icon),
        "methods": ["GET"]
    },
    {
        "rule": "/api/blueprint/upload",
        "endpoint": "atx.api_upload_blueprint",
        "view_func": admin_required(upload_blueprint),
        "methods": ["POST"]
    },
    {
        "rule": "/api/blueprint/delete",
        "endpoint": "atx.api_delete_blueprint",
        "view_func": admin_required(delete_blueprint),
        "methods": ["DELETE"]
    },
    {
        "rule": "/api/reports",
        "endpoint": "atx.api_get_reports",
        "view_func": login_required(get_reports),
        "methods": ["GET"]
    },
    {
        "rule": "/api/reports/<path>",
        "endpoint": "atx.api_get_reports_path",
        "view_func": login_required(get_reports),
        "methods": ["GET"]
    },
    {
        "rule": "/api/report/download/<filename>",
        "endpoint": "atx.api_download_report",
        "view_func": login_required(download_report),
        "methods": ["GET"]
    },
    {
        "rule": "/api/report/download/<path>/<filename>",
        "endpoint": "atx.api_download_report_path",
        "view_func": login_required(download_report),
        "methods": ["GET"]
    },
    {
        "rule": "/api/report/<filename>",
        "endpoint": "atx.api_delete_report",
        "view_func": login_required(delete_report),
        "methods": ["DELETE"]
    },
    {
        "rule": "/api/report/<path>/<filename>",
        "endpoint": "atx.api_delete_report_path",
        "view_func": login_required(delete_report),
        "methods": ["DELETE"]
    },
    {
        "rule": "/render_html",
        "endpoint": "atx.api_render_html",
        "view_func": login_required(render_html),
        "methods": ["GET"]
    }
]