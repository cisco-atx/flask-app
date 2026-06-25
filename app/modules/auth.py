"""
Authentication module for handling multiple auth backends.

Provides pluggable authentication backends (local, SSH, SSO, LDAP, AD,
RADIUS) and a registry-based AuthManager supporting multiple concurrent
providers, per-user provider binding, and priority-based claiming of
first-seen directory users.

Provider configuration is persisted in a providers database with secret
fields encrypted at rest via the application's PasswordCipher.

File path: app/modules/auth.py
"""

import datetime
import hashlib
import logging
import os
from abc import ABC, abstractmethod

import paramiko

try:
    from ldap3 import Server, Connection, ALL, NTLM, SIMPLE
    from ldap3.core.exceptions import LDAPException
except ImportError:
    Server = Connection = None
    ALL = NTLM = SIMPLE = None
    LDAPException = Exception

try:
    from pyrad.client import Client
    from pyrad.dictionary import Dictionary
    import pyrad.packet as packet
except ImportError:
    Client = None
    Dictionary = None
    packet = None

logger = logging.getLogger(__name__)

# Marker used for unavailable profile fields.
NA = "NA"

def hash_password(password):
    """Return the SHA-256 hash of a password string."""
    return hashlib.sha256((password or "").encode()).hexdigest()


class BaseAuthBackend(ABC):
    """Abstract base class for authentication backends.

    Concrete backends are instantiated per provider *instance* using the
    decrypted provider config dictionary.
    """

    #: Local backends manage their own user list and are never auto-claimed
    #: via the priority stack.
    is_local = False

    #: Whether this backend can lazily claim an unknown user via the
    #: priority stack.
    claimable = True

    def __init__(self, provider_id, config=None, **context):
        """Initialize backend with its provider id and decrypted config."""
        self.provider_id = provider_id
        self.config = config or {}
        self.context = context

    @abstractmethod
    def authenticate(self, username, password=None, **kwargs):
        """Authenticate a user. Return True on success, else False."""
        raise NotImplementedError

    def test_connection(self):
        """Optionally validate provider reachability. Return (ok, message)."""
        return True, "No connection test implemented for this provider."


class LocalAuth(BaseAuthBackend):
    """Local authentication backend using hashed passwords in users_db."""

    is_local = True
    claimable = False  # local users are created explicitly, never auto-claimed

    def __init__(self, provider_id, config=None, users_db=None, **context):
        """Initialize LocalAuth with the shared users database."""
        super().__init__(provider_id, config, **context)
        self.users_db = users_db

    def authenticate(self, username, password=None, **kwargs):
        """Authenticate user against the locally stored password hash."""
        user = self.users_db.get(username)
        if not user:
            return False
        return user.get("password_hash") == hash_password(password)


class SSHAuth(BaseAuthBackend):
    """SSH authentication backend using a remote connection.

    Config keys:
        host - SSH host
        port - SSH port (default 22)
    """

    def authenticate(self, username, password=None, **kwargs):
        """Authenticate a user via an SSH connection to the configured host."""
        host = kwargs.get("host") or self.config.get("host")
        port = int(kwargs.get("port") or self.config.get("port", 22))
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=host,
                username=username,
                password=password,
                port=port,
                timeout=5,
            )
            client.close()
            return True
        except Exception:
            logger.exception("SSH authentication failed for user: %s", username)
            return False

    def test_connection(self):
        """Verify the SSH host is reachable at the transport layer."""
        host = self.config.get("host")
        port = int(self.config.get("port", 22))
        try:
            transport = paramiko.Transport((host, port))
            transport.start_client(timeout=5)
            transport.close()
            return True, f"SSH host {host}:{port} reachable."
        except Exception as exc:
            return False, str(exc)


class SSOAuth(BaseAuthBackend):
    """Mock Single Sign-On (SSO) authentication backend (token-based)."""

    def authenticate(self, username, token=None, password=None, **kwargs):
        """Authenticate a user using a (mock) SSO token."""
        token = token or password
        return bool(token and token.startswith("valid"))


class LDAPAuth(BaseAuthBackend):
    """LDAP authentication backend using ldap3 simple bind.

    Config keys:
        host          - ldap(s)://host:port
        base_dn       - search base for the user
        user_dn_tmpl  - optional DN template, e.g.
                        "uid={username},ou=people,dc=example,dc=com"
        bind_dn       - optional service account DN for search-then-bind
        bind_password - service account password (encrypted at rest)
        user_attr     - attribute to match username (default "uid")
        use_ssl       - bool
    """

    def __init__(self, provider_id, config=None, **context):
        super().__init__(provider_id, config, **context)
        if Server is None:
            raise RuntimeError("ldap3 is not installed")

    def _server(self):
        """Build an ldap3 Server object from config."""
        return Server(
            self.config["host"],
            use_ssl=bool(self.config.get("use_ssl", False)),
            get_info=ALL,
        )

    def _resolve_user_dn(self, username):
        """Return the bind DN for a username via template or directory search."""
        tmpl = self.config.get("user_dn_tmpl")
        if tmpl:
            return tmpl.format(username=username)

        bind_dn = self.config.get("bind_dn")
        bind_pw = self.config.get("bind_password")
        base_dn = self.config["base_dn"]
        user_attr = self.config.get("user_attr", "uid")

        conn = Connection(
            self._server(),
            user=bind_dn,
            password=bind_pw,
            authentication=SIMPLE if bind_dn else None,
            auto_bind=True,
        )
        try:
            conn.search(
                search_base=base_dn,
                search_filter=f"({user_attr}={username})",
                attributes=[user_attr],
            )
            if not conn.entries:
                return None
            return conn.entries[0].entry_dn
        finally:
            conn.unbind()

    def authenticate(self, username, password=None, **kwargs):
        """Authenticate by binding as the resolved user DN."""
        if not password:
            return False
        try:
            user_dn = self._resolve_user_dn(username)
            if not user_dn:
                return False
            conn = Connection(
                self._server(),
                user=user_dn,
                password=password,
                authentication=SIMPLE,
            )
            ok = conn.bind()
            conn.unbind()
            return bool(ok)
        except LDAPException:
            logger.exception("LDAP authentication failed for %s", username)
            return False

    def test_connection(self):
        """Bind with the service account (or anonymous) to validate config."""
        try:
            conn = Connection(
                self._server(),
                user=self.config.get("bind_dn"),
                password=self.config.get("bind_password"),
                authentication=SIMPLE if self.config.get("bind_dn") else None,
                auto_bind=True,
            )
            conn.unbind()
            return True, "LDAP bind successful."
        except Exception as exc:
            return False, str(exc)


class ADAuth(LDAPAuth):
    """Active Directory backend using NTLM bind with DOMAIN/user.

    Config keys:
        host    - ldap(s)://dc.host
        domain  - NetBIOS domain (e.g. CORP)
        base_dn - search base
        use_ssl - bool
    """

    def authenticate(self, username, password=None, **kwargs):
        """Authenticate against Active Directory via NTLM bind."""
        if not password:
            return False
        domain = self.config.get("domain", "")
        account = f"{domain}/{username}" if domain else username
        try:
            conn = Connection(
                self._server(),
                user=account,
                password=password,
                authentication=NTLM,
            )
            ok = conn.bind()
            conn.unbind()
            return bool(ok)
        except LDAPException:
            logger.exception("AD authentication failed for %s", username)
            return False

    def test_connection(self):
        """Validate AD reachability by constructing a server object."""
        try:
            self._server()
            return True, f"AD server {self.config.get('host')} configured."
        except Exception as exc:
            return False, str(exc)


class RADIUSAuth(BaseAuthBackend):
    """RADIUS authentication backend using pyrad.

    Config keys:
        host           - RADIUS server host
        port           - auth port (default 1812)
        secret         - shared secret (encrypted at rest)
        dictionary     - path to a RADIUS dictionary file
        nas_identifier - optional NAS identifier
    """

    def __init__(self, provider_id, config=None, **context):
        super().__init__(provider_id, config, **context)
        if Client is None:
            raise RuntimeError("pyrad is not installed")

    def _client(self):
        """Build a pyrad Client from config."""
        return Client(
            server=self.config["host"],
            authport=int(self.config.get("port", 1812)),
            secret=self.config["secret"].encode(),
            dict=Dictionary(self.config["dictionary"]),
        )

    def authenticate(self, username, password=None, **kwargs):
        """Authenticate via an Access-Request to the RADIUS server."""
        if not password:
            return False
        try:
            client = self._client()
            req = client.CreateAuthPacket(code=packet.AccessRequest, User_Name=username)
            req["User-Password"] = req.PwCrypt(password)
            if self.config.get("nas_identifier"):
                req["NAS-Identifier"] = self.config["nas_identifier"]
            reply = client.SendPacket(req)
            return reply.code == packet.AccessAccept
        except Exception:
            logger.exception("RADIUS authentication failed for %s", username)
            return False

    def test_connection(self):
        """Construct the client to validate config (no live probe)."""
        try:
            self._client()
            return True, "RADIUS client configured."
        except Exception as exc:
            return False, str(exc)


# Registry of provider type -> backend class.
BACKEND_TYPES = {
    "local": LocalAuth,
    "ssh": SSHAuth,
    "sso": SSOAuth,
    "ldap": LDAPAuth,
    "ad": ADAuth,
    "radius": RADIUSAuth,
}


class AuthManager:
    """Registry-based authentication manager supporting many providers.

    Providers are persisted in ``providers_db`` as::

        provider_id -> {
            "id": provider_id,
            "type": "local|ssh|sso|ldap|ad|radius",
            "enabled": bool,
            "priority": int,        # lower = tried first when claiming
            "config": { ... },      # secret fields encrypted at rest
        }

    Users are persisted in ``users_db`` with a normalized record::

        username -> {
            "username": str,
            "meta": {
                "role": str,
                "auth_provider": provider_id,
                "created_at": iso8601,
                "last_login": iso8601 | None,
                "is_bootstrap": bool (admin only),
            },
            "profile": {"firstname": ..., "lastname": ..., "email": ...},
            "home_dir": str,
            "reports_dir": str,
            "password_hash": str (local-provider users only),
            "theme": str (optional),
        }
    """

    #: Config fields that must be encrypted at rest per provider type.
    SECRET_FIELDS = {
        "local": [],
        "ssh": [],
        "sso": [],
        "ldap": ["bind_password"],
        "ad": ["bind_password"],
        "radius": ["secret"],
    }

    def __init__(self, users_db, providers_db, base_dir, cipher):
        """Initialize the manager and build the live backend registry."""
        self.users_db = users_db
        self.providers_db = providers_db
        self.base_dir = base_dir
        self.cipher = cipher
        self.backends = {}
        self.bootstrap_providers()
        self.reload_backends()

    # ----- provider lifecycle --------------------------------------------

    def bootstrap_providers(self):
        """Ensure a default enabled 'local' provider always exists."""
        if "local" not in self.providers_db:
            self.providers_db["local"] = {
                "id": "local",
                "type": "local",
                "enabled": True,
                "priority": 0,
                "config": {},
            }

    def _decrypt_config(self, provider):
        """Return a copy of provider config with secret fields decrypted."""
        config = dict(provider.get("config", {}))
        for field in self.SECRET_FIELDS.get(provider["type"], []):
            if config.get(field):
                try:
                    config[field] = self.cipher.decrypt(config[field])
                except Exception:
                    logger.exception(
                        "Failed to decrypt %s for provider %s",
                        field, provider["id"],
                    )
        return config

    def _encrypt_config(self, ptype, config):
        """Return a copy of config with secret fields encrypted."""
        config = dict(config or {})
        for field in self.SECRET_FIELDS.get(ptype, []):
            if config.get(field):
                config[field] = self.cipher.encrypt(config[field])
        return config

    def reload_backends(self):
        """Rebuild the live backend registry from providers_db."""
        backends = {}
        for pid, provider in self.providers_db.items():
            if not provider.get("enabled", True):
                continue
            cls = BACKEND_TYPES.get(provider["type"])
            if not cls:
                logger.warning("Unknown provider type: %s", provider["type"])
                continue
            try:
                backends[pid] = cls(
                    provider_id=pid,
                    config=self._decrypt_config(provider),
                    users_db=self.users_db,
                    base_dir=self.base_dir,
                )
            except Exception:
                logger.exception("Failed to initialize provider %s", pid)
        self.backends = backends

    def list_providers(self, redact=True):
        """Return all providers, with secret fields redacted by default."""
        result = []
        for pid, provider in self.providers_db.items():
            item = dict(provider)
            if redact:
                cfg = dict(item.get("config", {}))
                for field in self.SECRET_FIELDS.get(item["type"], []):
                    if cfg.get(field):
                        cfg[field] = "********"
                item["config"] = cfg
            result.append(item)
        result.sort(key=lambda p: p.get("priority", 100))
        return result

    def upsert_provider(self, provider_id, ptype, enabled=True,
                       priority=100, config=None):
        """Create or update a provider, encrypting secrets, then reload.

        Secret fields that arrive blank or masked ("********") are left
        unchanged so editing a provider does not wipe stored secrets.
        """
        if ptype not in BACKEND_TYPES:
            raise ValueError(f"Unsupported provider type: {ptype}")

        existing = self.providers_db.get(provider_id, {})
        # Start from existing *decrypted* config so we can re-encrypt as a set.
        merged_config = self._decrypt_config(existing) if existing else {}

        incoming = dict(config or {})
        for field in self.SECRET_FIELDS.get(ptype, []):
            if incoming.get(field) in (None, "", "********"):
                incoming.pop(field, None)  # keep existing secret
        merged_config.update(incoming)

        self.providers_db[provider_id] = {
            "id": provider_id,
            "type": ptype,
            "enabled": bool(enabled),
            "priority": int(priority),
            "config": self._encrypt_config(ptype, merged_config),
        }
        self.reload_backends()

    def delete_provider(self, provider_id):
        """Delete a provider. The built-in 'local' provider is protected."""
        if provider_id == "local":
            raise ValueError("The built-in 'local' provider cannot be "
                            "deleted.")
        if provider_id in self.providers_db:
            del self.providers_db[provider_id]
        self.reload_backends()

    def test_provider(self, provider_id):
        """Run the backend's connection test. Returns (ok, message)."""
        backend = self.backends.get(provider_id)
        if not backend:
            return False, "Provider not found or disabled."
        return backend.test_connection()

    # ----- user lifecycle -------------------------------------------------

    def _provision_user(self, username, role, profile, auth_provider,
                       password_hash=None):
        """Create directories and a normalized user record."""
        home_dir = os.path.join(str(self.base_dir), username)
        reports_dir = os.path.join(home_dir, "reports")
        os.makedirs(home_dir, exist_ok=True)
        os.makedirs(reports_dir, exist_ok=True)

        user_data = self.users_db.get(username, {})
        meta = user_data.get("meta", {})
        meta.update({
            "role": role,
            "auth_provider": auth_provider,
            "created_at": meta.get("created_at")
            or datetime.datetime.now().isoformat(),
            "last_login": meta.get("last_login"),
        })

        record = {
            "username": username,
            "meta": meta,
            "profile": {
                "firstname": profile.get("firstname") or NA,
                "lastname": profile.get("lastname") or NA,
                "email": profile.get("email") or NA,
            },
            "home_dir": home_dir,
            "reports_dir": reports_dir,
        }

        # Preserve an existing theme preference if present.
        if "theme" in user_data:
            record["theme"] = user_data["theme"]

        # Only local-provider users carry a password hash.
        if password_hash is not None:
            record["password_hash"] = password_hash
        elif "password_hash" in user_data:
            record["password_hash"] = user_data["password_hash"]

        self.users_db[username] = record
        return record

    def register(self, username, password, role="user", profile=None,
                auth_provider="local"):
        """Register a user under a specific provider.

        For local providers the password is hashed and stored. For external
        providers no password is stored (the directory remains source of
        truth); the username is simply bound to that provider.
        """
        if username in self.users_db:
            return False, "User already exists"

        backend = self.backends.get(auth_provider)
        if backend is None:
            return False, f"Provider '{auth_provider}' is not available"

        password_hash = hash_password(password) if backend.is_local else None

        self._provision_user(
            username,
            role=role,
            profile=profile or {},
            auth_provider=auth_provider,
            password_hash=password_hash,
        )
        return True, "Registered"

    def update_local_user(self, username, profile=None, role=None,
                         password=None):
        """Admin update of a local user's profile / role / password."""
        user = self.users_db.get(username)
        if not user:
            return False, "User not found"
        if user["meta"].get("auth_provider") != "local":
            return False, "User is not a local-provider user"

        if profile:
            user["profile"].update({
                "firstname": profile.get("firstname")
                or user["profile"].get("firstname", NA),
                "lastname": profile.get("lastname")
                or user["profile"].get("lastname", NA),
                "email": profile.get("email")
                or user["profile"].get("email", NA),
            })
        if role:
            user["meta"]["role"] = role
        if password:
            user["password_hash"] = hash_password(password)

        self.users_db[username] = user
        return True, "Updated"

    def change_user_role(self, username, new_role):
        """Change a user's role regardless of provider."""
        user = self.users_db.get(username)
        if not user:
            return False, "User not found"
        user["meta"]["role"] = new_role
        self.users_db[username] = user
        return True, "Updated"

    def authenticate(self, username, password=None, provider_id=None, **kwargs):
        """Authenticate a user.

        Resolution order:
          1. Bootstrap admin short-circuit — ONLY while the bootstrap admin
             is the sole user in the DB (fresh / emptied deploy). Reopens
             automatically if the DB is ever reduced back to that single
             user.
          2. Known user -> authenticate against their stored auth_provider.
          3. Unknown user -> priority-stack claiming (non-local backends);
             the first provider to succeed claims and provisions the user.
        """
        user = self.users_db.get(username)

        # 1. Bootstrap admin short-circuit (only on an otherwise-empty DB).
        if (
            user
            and user["meta"].get("is_bootstrap")
            and len(self.users_db) == 1
            and user.get("password_hash") == hash_password(password)
        ):
            self._stamp_login(username)
            return True

        # 2. Known user: use their bound provider.
        if user:
            bound = user["meta"].get("auth_provider")
            backend = self.backends.get(bound)
            if not backend:
                logger.warning(
                    "User %s bound to unavailable provider %s",
                    username, bound,
                )
                return False
            if backend.authenticate(username, password, **kwargs):
                self._stamp_login(username)
                return True
            return False

        # 3. Unknown user: priority-stack claiming (non-local backends only).
        ordered = sorted(
            (
                (pid, self.backends[pid])
                for pid in self.backends
                if self.backends[pid].claimable
                and not self.backends[pid].is_local
            ),
            key=lambda kv: self.providers_db.get(kv[0], {}).get(
                "priority", 100
            ),
        )
        for pid, backend in ordered:
            try:
                if backend.authenticate(username, password, **kwargs):
                    self._provision_user(
                        username,
                        role="user",
                        profile={},
                        auth_provider=pid,
                    )
                    self._stamp_login(username)
                    logger.info(
                        "User %s claimed by provider %s", username, pid
                    )
                    return True
            except Exception:
                logger.exception(
                    "Provider %s errored authenticating %s", pid, username
                )
        return False

    def _stamp_login(self, username):
        """Update the last_login timestamp on the user record."""
        user = self.users_db[username]
        user["meta"]["last_login"] = datetime.datetime.now().isoformat()
        self.users_db[username] = user

    def delete_user(self, username):
        """Delete a user and best-effort remove their home directory."""
        if username in self.users_db:
            home_dir = self.users_db[username].get("home_dir")
            if home_dir and os.path.exists(home_dir):
                try:
                    os.rmdir(home_dir)
                except OSError:
                    logger.warning(
                        "Failed to remove directory (not empty?): %s",
                        home_dir,
                    )
            del self.users_db[username]

    def migrate_users(self):
        """Idempotent migration of legacy user records.

        - Ensures meta.auth_provider exists (defaults to 'local').
        - Ensures a profile dict with firstname/lastname/email, pulling
          from any legacy top-level fields if present, else 'NA'.
        """
        for username in list(self.users_db.keys()):
            user = self.users_db[username]
            changed = False

            meta = user.setdefault("meta", {})
            if not meta.get("auth_provider"):
                meta["auth_provider"] = "local"
                changed = True

            profile = user.get("profile")
            if not isinstance(profile, dict):
                profile = {}
                changed = True
            for field in ("firstname", "lastname", "email"):
                if not profile.get(field):
                    profile[field] = user.get(field) or NA
                    changed = True
            user["profile"] = profile

            if changed:
                self.users_db[username] = user
                logger.info("Migrated user record: %s", username)

    def setup_bootstrap_admin(self):
        """Create the initial local admin if no users exist.

        The bootstrap admin (admin/admin) authenticates via the short-circuit
        in ``authenticate`` ONLY while it is the sole user in the database.
        """
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
                auth_provider="local",
            )
            user_data = self.users_db["admin"]
            user_data["meta"]["is_bootstrap"] = True
            self.users_db["admin"] = user_data