"""
Flask application initialization and configuration.

This module defines the FlaskApp class, which initializes and configures
the Flask application, including database setup, authentication,
blueprints, logging, and session management policies.

Path: app/app.py
"""

# Standard library imports
import datetime
import logging
import os
import uuid

# Third-party imports
from flask import Flask, flash, redirect, request, session, url_for
from sqlitedict import SqliteDict

# Local imports
from . import modules
from . import routes
from . import utils

logger = logging.getLogger(__name__)


class FlaskApp(Flask):
    """Custom Flask application class with extended setup."""

    def __init__(self, **kwargs):
        """Initialize the Flask application and its components."""
        super().__init__(
            import_name=__name__,
            template_folder="templates",
            static_folder="static",
            **kwargs,
        )

        self.modules = modules
        self.routes = routes
        self.utils = utils

        self.secret_key = self.utils.SECRET_KEY
        self.azureai = self.modules.AzureAIClient(
            self.utils.AZURE_AI_ENV_PATH
        )
        self.cipher = self.modules.PasswordCipher(
            key_file=self.utils.CIPHER_KEY
        )

        self.setup_server_instance()
        self.setup_directories()
        self.setup_db()
        self.setup_auth()
        self.setup_routes()
        self.setup_blueprints()
        self.setup_global_logger()
        self.inject_globals()
        self.before_request(self.enforce_session_policies)

    def setup_server_instance(self):
        """Ensure a unique server instance ID is set."""
        if not os.path.exists(self.utils.SERVER_INSTANCE_FILE):
            logger.info("Creating new server instance ID file.")
            with open(self.utils.SERVER_INSTANCE_FILE, "w") as f:
                f.write(str(uuid.uuid4()))

        with open(self.utils.SERVER_INSTANCE_FILE, "r") as f:
            self.server_instance_id = f.read().strip()

        logger.info("Server instance ID set: %s", self.server_instance_id)

    def setup_directories(self):
        """Ensure necessary directories exist."""
        directories = [
            self.utils.HOME_DIR,
            self.utils.BP_DIR,
            self.utils.PROJECT_DIR,
            self.utils.DB_DIR,
            self.utils.USERS_DIR,
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.debug("Ensured directory exists: %s", directory)

    def setup_db(self):
        """Initialize the databases using SqliteDict."""
        logger.info("Initializing databases.")
        self.bp_db = SqliteDict(self.utils.BP_DB, autocommit=True)
        self.users_db = SqliteDict(self.utils.USERS_DB, autocommit=True)

    def setup_auth(self):
        """Initialize the authentication manager."""
        logger.info("Setting up authentication manager.")
        self.auth = self.modules.AuthManager(
            users_db=self.users_db,
            base_dir=self.utils.USERS_DIR,
            mode=self.utils.AUTH_PARAMS.get("mode"),
        )
        self.auth.setup_bootstrap_admin()

    def set_authenticated_user(self, username):
        """Set session variables for the authenticated user."""
        session.update(
            {
                "username": username,
                "userdata": self.users_db[username],
                "server_instance_id": self.server_instance_id,
                "last_activity": datetime.datetime.now().isoformat(),
            }
        )
        self.global_logger.attach_root()

    def setup_routes(self):
        """Register all routes from the routes module."""
        logger.info("Registering routes.")
        for route in self.routes.routes:
            self.add_url_rule(**route)

    def setup_blueprints(self):
        """Load and register blueprints."""
        logger.info("Loading and registering blueprints.")
        with self.app_context():
            blueprint_data = self.routes.load_blueprints().get_json()
            self.bp_db.update(blueprint_data)

    def setup_global_logger(self):
        """Set up a global application logger."""
        logger.info("Initializing global logger.")
        self.global_logger = self.modules.StreamLogger(
            name="atx_logger",
            filter_regex="werkzeug",
            log_file=self.utils.GLOBAL_LOGGER,
        )

    def inject_globals(self):
        """Inject common variables into all templates."""

        @self.context_processor
        def inject_base_globals():
            return {
                "app_version": self.utils.APP_VERSION,
                "auth_params": self.utils.AUTH_PARAMS,
                "deployment_stage": self.utils.DEPLOYMENT_STAGE,
            }

    def enforce_session_policies(self):
        """Enforce session security and authentication policies."""
        endpoint = request.endpoint

        if endpoint in self.utils.EXEMPT_ENDPOINTS:
            return

        if any(
            request.path.endswith(ext)
            for ext in [
                ".css",
                ".js",
                ".ico",
                ".png",
                ".jpg",
                ".jpeg",
                ".svg",
            ]
        ):
            return

        view_func = self.view_functions.get(endpoint)
        if view_func and getattr(view_func, "is_public", False):
            return

        if session.get("server_instance_id") != self.server_instance_id:
            session.clear()
            flash("Server restarted. Please log in again.", "info")
            return redirect(url_for("atx.render_login"))

        if "username" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("atx.render_login"))

        now = datetime.datetime.now()
        last_activity = session.get("last_activity")

        if last_activity:
            last_activity_dt = datetime.datetime.fromisoformat(last_activity)
            if now - last_activity_dt > datetime.timedelta(
                    minutes=self.utils.SESSION_LIFETIME_MINUTES
            ):
                session.clear()
                flash("Session expired due to inactivity.", "info")
                return redirect(url_for("atx.render_login"))

        if request.endpoint not in {"atx.activity", "static"}:
            session["last_activity"] = now.isoformat()

        session.permanent = True
