"""
Application constants configuration.

Defines global constants used across the application such as
environment settings, authentication configuration, and session
management. Centralizing these values improves maintainability
and consistency across modules.

File Path: app/utils/constants.py
"""

import os
import logging

logger = logging.getLogger(__name__)

# Application constants
APP_VERSION = "1.1.0"
DEPLOYMENT_STAGE = "dev"

# Path to Azure AI environment configuration file
AZURE_AI_ENV_PATH = os.path.join(
    os.path.expanduser("~"),
    ".atx",
    "azureai.env",
)

# Session configuration
SESSION_LIFETIME_MINUTES = 30

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "atx_secret")
if SECRET_KEY == "atx_secret":
    logger.warning("Using default SECRET_KEY; consider setting a secure "
                   "value in environment variables.")

# Authentication parameters
AUTH_PARAMS = {
    "mode": os.getenv("AUTH_MODE", "local"),
}
logger.info("Authentication mode set to '%s'.", AUTH_PARAMS["mode"])

# Endpoints that do not require user authentication
EXEMPT_ENDPOINTS = {
    "atx.render_login",
    "atx.render_register",
    "atx.redirect_logout",
    "atx.sse_activity",
    "static",
    "root",
}
