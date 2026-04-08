import os

# Application directory
APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BP_DIR = os.path.join(APP_DIR, "blueprints")

# User's home directory for application data
HOME_DIR = os.path.join(os.path.expanduser("~"), ".atx")
GLOBAL_LOGGER = os.path.join(HOME_DIR, "logger.log")
CIPHER_KEY = os.path.join(HOME_DIR, "cipher.key")
PROJECT_DIR = os.path.join(HOME_DIR, "projects")
DB_DIR = os.path.join(HOME_DIR, "db")
USERS_DIR = os.path.join(HOME_DIR, "users")

# Database file paths
BP_DB = os.path.join(DB_DIR, "blueprints.sqlite")
USERS_DB = os.path.join(DB_DIR, "users.sqlite")