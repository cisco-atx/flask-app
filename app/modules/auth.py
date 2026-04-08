import os
import hashlib
import datetime
from abc import ABC, abstractmethod
import paramiko


class BaseAuthBackend(ABC):
    """Abstract base class for authentication backends. Defines the interface that all auth backends must implement."""

    @abstractmethod
    def authenticate(self, username, password=None, **kwargs):
        pass


class LocalAuth(BaseAuthBackend):
    """A simple local authentication backend that uses a username and password stored in the users database. Passwords are hashed using SHA-256 for basic security."""

    def __init__(self, users_db):
        self.users_db = users_db

    def _hash(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, username, password=None, **kwargs):
        user = self.users_db.get(username)

        if not user:
            return False

        return user.get("password_hash") == self._hash(password)


class SSHAuth(BaseAuthBackend):
    """ An SSH authentication backend that attempts to establish an SSH connection using the provided credentials."""

    def authenticate(self, username, password=None, host=None, port=22, **kwargs):
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
            return False


class SSOAuth(BaseAuthBackend):
    """A mock Single Sign-On (SSO) authentication backend."""

    def authenticate(self, username, token=None, **kwargs):
        return bool(token and token.startswith("valid"))


class AuthManager:
    """The main authentication manager that handles user registration, authentication, and profile management."""

    def __init__(self, users_db, base_dir, mode="local"):
        self.users_db = users_db
        self.base_dir = base_dir
        self.mode = mode
        self.backend = self._get_backend()

    def _get_backend(self):
        backends = {
            "local": LocalAuth(self.users_db),
            "ssh": SSHAuth(),
            "sso": SSOAuth(),
        }

        if self.mode not in backends:
            raise ValueError(f"Unsupported auth mode: {self.mode}")

        return backends[self.mode]

    def _provision_user(self, username, role, profile):
        """Provision user resources such as home and reports directories."""
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
                "email": profile.get("email", "Not Availabe")
            },
            "home_dir": home_dir,
            "reports_dir": reports_dir
        })
        self.users_db[username] = user_data

    def register(self, username, password, role="user", profile=None):
        """Register a new user with the provided username, password, role, and profile information."""
        self.users_db[username] = {
            "password_hash": hashlib.sha256(password.encode()).hexdigest()
        }
        self._provision_user(username, role, profile or {})

        return True, "Registered"

    def authenticate(self, username, password=None, **kwargs):
        """Authenticate a user using the configured backend."""
        success = False
        role = "user"
        user = self.users_db.get(username)
        if user and user["meta"].get("is_bootstrap") and user.get("password_hash") == hashlib.sha256(
                password.encode()).hexdigest():
            role = user["meta"]["role"]
            success = True

        if not success:
            success = self.backend.authenticate(username, password, **kwargs)

        if not success:
            return False

        if not self.users_db.get(username):
            self._provision_user(username, role=role, profile={})

        user_data = self.users_db[username]
        user_data["meta"]["last_login"] = datetime.datetime.now().isoformat()
        self.users_db[username] = user_data

        return True

    def delete_user(self, username):
        """Delete a user from the repository and remove their resources."""
        if username in self.users_db:
            user_data = self.users_db[username]
            home_dir = user_data.get("home_dir")
            if home_dir and os.path.exists(home_dir):
                os.rmdir(home_dir)
            del self.users_db[username]

    def setup_bootstrap_admin(self):
        """Bootstrap an initial admin user if the users database is empty."""
        if not self.users_db:
            self.register(
                username="admin",
                password="admin",
                role="superadmin",
                profile={"email": "admin@local", "firstname": "System", "lastname": "User"}
            )
            user_data = self.users_db["admin"]
            user_data["meta"]["is_bootstrap"] = True
            self.users_db["admin"] = user_data
