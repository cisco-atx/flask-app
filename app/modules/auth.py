import os
import hashlib
import paramiko
import datetime
from abc import ABC, abstractmethod


class BaseAuthBackend(ABC):
    """Abstract base class for authentication backends."""

    def __init__(self, users_db, base_dir):
        self.users_db = users_db
        self.base_dir = base_dir

    @abstractmethod
    def register(self, username, password=None, role="user", **kwargs):
        pass

    @abstractmethod
    def authenticate(self, username, password=None, **kwargs):
        pass


class LocalAuth(BaseAuthBackend):
    """Simple local authentication using username and password."""

    def _hash(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username, password=None, role="user", **kwargs):
        """Registers a new user with a hashed password. Additional profile info can be passed via kwargs."""
        if username in self.users_db:
            return False, "User already exists"

        self.users_db[username] = {
            "password": self._hash(password),
            "meta": {
                "role": role,
                "created_at": datetime.datetime.now().isoformat(),
                "last_login": None,
            },
            "mode": "local",
            "profile": {
                "firstname": kwargs.get("firstname", ""),
                "lastname": kwargs.get("lastname", ""),
                "email": kwargs.get("email", "")
            }
        }

        return True, "User registered"

    def authenticate(self, username, password=None, **kwargs):
        """Authenticates a user by comparing the hashed password. Updates last login time on success."""
        if username not in self.users_db:
            return False

        hased_password = self._hash(password)
        if self.users_db[username]["password"] == hased_password:
            user = self.users_db[username]
            user["meta"]["last_login"] = datetime.datetime.now().isoformat()
            self.users_db[username] = user
            return True
        return False


class RemoteSSHAuth(BaseAuthBackend):
    """Authentication using SSH credentials to verify access to a remote host."""

    def _verify(self, username, password, host, port=22):
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

    def register(self, username, password=None, role="user", host=None, **kwargs):
        """Registers a user by verifying SSH access to the specified host. Additional profile info can be passed via kwargs."""
        if not host:
            return False, "Host required"

        if not self._verify(username, password, host):
            return False, "SSH verification failed"

        self.users_db[username] = {
            "password": None,
            "meta": {
                "role": role,
                "created_at": datetime.datetime.now().isoformat(),
                "last_login": None,
            },
            "mode": f"ssh:{host}",
            "profile": {
                "firstname": kwargs.get("firstname", ""),
                "lastname": kwargs.get("lastname", ""),
                "email": kwargs.get("email", "")
            }
        }

        return True, "User registered via SSH"

    def authenticate(self, username, password=None, host=None, **kwargs):
        """Authenticates a user by verifying SSH access to the specified host. Updates last login time on success."""
        if not host:
            return False

        if self._verify(username, password, host):
            user = self.users_db[username]
            user["meta"]["last_login"] = datetime.datetime.now().isoformat()
            self.users_db[username] = user
            return True
        return False


class SSOAuth(BaseAuthBackend):
    """Authentication using Single Sign-On (SSO) tokens. This is a placeholder implementation and should be replaced with real SSO validation logic."""

    def _verify(self, token=None, **kwargs):
        # Replace with real SSO validation (OAuth/SAML/etc.)
        if not token:
            return False

        return token.startswith("valid")

    def register(self, username, password=None, role="user", token=None, **kwargs):
        """Registers a user by verifying the provided SSO token. Additional profile info can be passed via kwargs."""
        if not self._verify(token=token):
            return False, "SSO verification failed"

        self.users_db[username] = {
            "password": None,
            "meta": {
                "role": role,
                "created_at": datetime.datetime.now().isoformat(),
                "last_login": None,
            },
            "mode": "sso",
            "profile": {
                "firstname": kwargs.get("firstname", ""),
                "lastname": kwargs.get("lastname", ""),
                "email": kwargs.get("email", "")
            },
        }

        return True, "User registered via SSO"

    def authenticate(self, username, password=None, token=None, **kwargs):
        """Authenticates a user by verifying the provided SSO token. Updates last login time on success."""
        if self._verify(token=token):
            user = self.users_db[username]
            user["meta"]["last_login"] = datetime.datetime.now().isoformat()
            self.users_db[username] = user
            return True
        return False


class AuthManager:
    """Central authentication manager that abstracts different authentication backends (local, SSH, SSO). It initializes the appropriate backend based on the specified mode and provides a unified interface for registration and authentication."""

    def __init__(self, users_db, base_dir, mode="local"):
        self.users_db = users_db
        self.base_dir = base_dir
        self.mode = mode
        self.backend = self._get_backend(mode)

    def _get_backend(self, mode):
        if mode == "local":
            return LocalAuth(self.users_db, self.base_dir)
        elif mode == "ssh":
            return RemoteSSHAuth(self.users_db, self.base_dir)
        elif mode == "sso":
            return SSOAuth(self.users_db, self.base_dir)
        else:
            raise ValueError(f"Unsupported auth mode: {mode}")

    def _setup_user_env(self, username):
        home_dir = os.path.join(str(self.base_dir), username)
        reports_dir = os.path.join(home_dir, "reports")
        user = self.users_db[username]
        user["home_dir"] = home_dir
        user["reports_dir"] = reports_dir
        self.users_db[username] = user
        os.makedirs(home_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)

    def register(self, username, password=None, role="user", **kwargs):
        """Registers a user using the selected authentication backend. On successful registration, it sets up the user's environment (directories, etc.). Additional profile info can be passed via kwargs."""
        success, message = self.backend.register(username, password, role, **kwargs)
        if success:
            self._setup_user_env(username)
        return success, message

    def authenticate(self, username, password=None, **kwargs):
        """Authenticates a user using the selected authentication backend. On successful authentication, it updates the user's last login time. Additional parameters (like host for SSH or token for SSO) can be passed via kwargs."""
        return self.backend.authenticate(username, password, **kwargs)

    def setup_bootstrap_admin(self):
        """Sets up a default admin user if no users exist in the database. This is useful for initial setup."""
        if not len(dict(self.users_db)):
            self.register(
                **{
                    "username": "admin",
                    "password": "admin123",
                    "role": "superadmin",
                    "firstname": "Bootstrap",
                    "lastname": "Admin",
                    "email": "admin@local"
                }
            )
