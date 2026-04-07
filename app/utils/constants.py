import os

# Application constants
APP_VERSION = "1.1.0"
DEPLOYMENT_STAGE = "dev"
AZURE_AI_ENV_PATH = os.path.join(os.path.expanduser("~"), ".atx", "azureai.env")
SESSION_LIFETIME_MINUTES = 30
SECRET_KEY = os.getenv("SECRET_KEY", "atx_secret")
AUTH_MODE = os.getenv("AUTH_MODE", "local")
AUTH_PARAMS = {}

# Endpoints that do not require user authentication.
EXEMPT_ENDPOINTS = {
    "atx.render_login",
    "atx.render_register",
    "atx.redirect_logout",
    "static",
    "root",
}
