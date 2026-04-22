"""
Authentication module for handling multiple auth backends.

Provides implementations for local, SSH, and SSO authentication along
with a centralized AuthManager for user lifecycle management.
Includes user provisioning, registration, authentication, and cleanup.
Designed for extensibility via pluggable authentication backends.

File path: app/modules/auth.py
"""

import datetime
import hashlib
import logging
import os
from abc import ABC, abstractmethod

import paramiko

logger = logging.getLogger(__name__)


class BaseAuthBackend(ABC):
    """Abstract base class for authentication backends."""

    @abstractmethod
    def authenticate(self, username, password=None, **kwargs):
        """Authenticate a user with given credentials."""
        pass


class LocalAuth(BaseAuthBackend):
    """Local authentication backend using hashed passwords."""

    def __init__(self, users_db):
        """Initialize LocalAuth with users database."""
        self.users_db = users_db

    def _hash(self, password):
        """Return SHA-256 hash of the password."""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, username, password=None, **kwargs):
        """Authenticate user against local database."""
        user = self.users_db.get(username)

        if not user:
            return False

        is_valid = user.get("password_hash") == self._hash(password)

        return is_valid


class SSHAuth(BaseAuthBackend):
    """SSH authentication backend using remote connection."""

    def authenticate(self, username, password=None, host=None, port=22,
                     **kwargs):
        """Authenticate user via SSH connection."""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(
                hostname=host,
                username=username,
                password=password,
                port=port,
                timeout=5
            )

            client.close()
            return True

        except Exception:
            logger.exception(
                "SSH authentication failed for user: %s", username
            )
            return False


class SSOAuth(BaseAuthBackend):
    """Mock Single Sign-On (SSO) authentication backend."""

    def authenticate(self, username, token=None, **kwargs):
        """Authenticate user using SSO token."""
        is_valid = bool(token and token.startswith("valid"))

        return is_valid


class AuthManager:
    """Authentication manager handling user lifecycle operations."""

    def __init__(self, users_db, base_dir, mode="local"):
        """Initialize AuthManager with configuration."""
        self.users_db = users_db
        self.base_dir = base_dir
        self.mode = mode
        self.backend = self._get_backend()

    def _get_backend(self):
        """Return the appropriate authentication backend."""
        backends = {
            "local": LocalAuth(self.users_db),
            "ssh": SSHAuth(),
            "sso": SSOAuth(),
        }

        if self.mode not in backends:
            raise ValueError(f"Unsupported auth mode: {self.mode}")

        return backends[self.mode]

    def _provision_user(self, username, role, profile):
        """Provision user directories and metadata."""
        home_dir = os.path.join(str(self.base_dir), username)
        reports_dir = os.path.join(home_dir, "reports")

        os.makedirs(home_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)

        user_data = self.users_db.get(username, {})
        user_data.update({
            "username": username,
            "meta": {
                "role": role,
                "created_at": datetime.datetime.now().isoformat(),
                "last_login": None,
            },
            "profile": {
                "firstname": profile.get("firstname", username),
                "lastname": profile.get("lastname", username),
                "email": profile.get("email", "Not Availabe"),
            },
            "home_dir": home_dir,
            "reports_dir": reports_dir,
        })

        self.users_db[username] = user_data

    def register(self, username, password, role="user", profile=None):
        """Register a new user."""

        self.users_db[username] = {
            "password_hash": hashlib.sha256(password.encode()).hexdigest()
        }

        self._provision_user(username, role, profile or {})

        return True, "Registered"

    def authenticate(self, username, password=None, **kwargs):
        """Authenticate a user using configured backend."""

        success = False
        role = "user"
        user = self.users_db.get(username)

        if (
                user
                and user["meta"].get("is_bootstrap")
                and user.get("password_hash")
                == hashlib.sha256(password.encode()).hexdigest()
        ):
            role = user["meta"]["role"]
            success = True

        if not success:
            success = self.backend.authenticate(
                username, password, **kwargs
            )

        if not success:
            return False

        if not self.users_db.get(username):
            self._provision_user(username, role=role, profile={})

        user_data = self.users_db[username]
        user_data["meta"]["last_login"] = (
            datetime.datetime.now().isoformat()
        )
        self.users_db[username] = user_data

        return True

    def delete_user(self, username):
        """Delete user and associated resources."""

        if username in self.users_db:
            user_data = self.users_db[username]
            home_dir = user_data.get("home_dir")

            if home_dir and os.path.exists(home_dir):
                try:
                    os.rmdir(home_dir)
                except OSError:
                    logger.warning(
                        "Failed to remove directory (not empty?): %s",
                        home_dir,
                    )

            del self.users_db[username]

    def setup_bootstrap_admin(self):
        """Create initial admin user if database is empty."""
        if not self.users_db:
            self.register(
                username="admin",
                password="admin",
                role="superadmin",
                profile={
                    "email": "admin@local",
                    "firstname": "System",
                    "lastname": "User",
                },
            )

            user_data = self.users_db["admin"]
            user_data["meta"]["is_bootstrap"] = True
            self.users_db["admin"] = user_data
