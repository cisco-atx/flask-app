# Standard library imports
import datetime
import os
import uuid

# Third-party imports
from flask import Flask, session, request, flash, redirect, url_for
from sqlitedict import SqliteDict

# Local imports
from . import modules
from . import routes
from . import utils

class FlaskApp(Flask):

    def __init__(self, **kwargs):
        super().__init__(
            import_name=__name__,
            template_folder="templates",
            static_folder="static",
            **kwargs
        )

        self.modules = modules
        self.routes = routes
        self.utils = utils

        self.secret_key = self.utils.SECRET_KEY
        self.azureai = self.modules.AzureAIClient(self.utils.AZURE_AI_ENV_PATH)
        self.cipher = self.modules.PasswordCipher(key_file=self.utils.CIPHER_KEY)

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
        """Ensure a unique server instance ID is set for session management and restart detection."""
        if not os.environ.get("ATX_SERVER_INSTANCE_ID"):
            os.environ["ATX_SERVER_INSTANCE_ID"] = uuid.uuid4().hex

        self.server_instance_id = os.environ["ATX_SERVER_INSTANCE_ID"]

    def setup_directories(self):
        """Ensure necessary directories exist."""
        for d in [
            self.utils.HOME_DIR,
            self.utils.BP_DIR,
            self.utils.PROJECT_DIR,
            self.utils.DB_DIR,
            self.utils.USERS_DIR
        ]:
            os.makedirs(d, exist_ok=True)

    def setup_db(self):
        """Initialize the bps and users databases using SqliteDict."""
        self.bp_db = SqliteDict(self.utils.BP_DB, autocommit=True)
        self.users_db = SqliteDict(self.utils.USERS_DB, autocommit=True)

    def setup_auth(self):
        """Initialize the authentication manager with the users database and configuration."""
        self.auth = self.modules.AuthManager(users_db=self.users_db, base_dir=self.utils.USERS_DIR, mode=self.utils.AUTH_MODE)
        self.auth.setup_bootstrap_admin()

    def set_authenticated_user(self, username):
        """Set session variables for the authenticated user."""
        session.update(
            {
                "username": username,
                "userdata": self.users_db[username],
                "server_instance_id": self.server_instance_id,
                "last_activity": datetime.datetime.now().isoformat()
            }
        )
        self.global_logger.attach_root()

    def setup_routes(self):
        """Register all routes from the routes module."""
        for route in self.routes.routes:
            self.add_url_rule(**route)

    def setup_blueprints(self):
        """Load and register blueprints from the blueprints directory, and update the blueprints database with their metadata."""
        with self.app_context():
            self.bp_db.update(self.routes.load_blueprints().get_json())

    def setup_global_logger(self):
        """ Set up a global logger that filters out werkzeug logs and writes to a file."""
        self.global_logger = self.modules.StreamLogger(
            name="atx_logger",
            filter_regex="werkzeug",
            log_file=self.utils.GLOBAL_LOGGER
        )

    def inject_globals(self):
        """Inject common variables into all templates."""
        @self.context_processor
        def inject_base_globals():
            return {
                "app_version": self.utils.APP_VERSION,
                "deployment_stage": self.utils.DEPLOYMENT_STAGE
            }

    def enforce_session_policies(self):
        # Skip checks for exempt endpoints
        if request.endpoint in self.utils.EXEMPT_ENDPOINTS:
            return

        # Server restart detection
        if session.get("server_instance_id") != self.server_instance_id:
            session.clear()
            flash("Server restarted. Please log in again.", "info")
            return redirect(url_for("atx.render_login"))

        # Not logged in
        if "username" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("atx.render_login"))

        # Inactivity timeout
        now = datetime.datetime.now()
        last_activity = session.get("last_activity")

        if last_activity:
            last_activity = datetime.datetime.fromisoformat(last_activity)
            if now - last_activity > datetime.timedelta(minutes=self.utils.SESSION_LIFETIME_MINUTES):
                session.clear()
                flash("Session expired due to inactivity.", "info")
                return redirect(url_for("atx.render_login"))

        session["last_activity"] = now.isoformat()
        session.permanent = True