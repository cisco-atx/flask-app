"""
Password cipher utilities.

Provides functionality to encrypt and decrypt passwords using Fernet
symmetric encryption from the cryptography library. The key is loaded
from an environment variable or file, and generated if not present.

Module path: app/modules/cipher.py
"""

import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class PasswordCipher:
    """Handle encryption and decryption using Fernet symmetric encryption."""

    ENV_KEY_NAME = "NETAUDIT_FERNET_KEY"
    DEFAULT_KEY_FILE = "secrets/fernet.key"

    def __init__(self, key_file: str | None = None):
        """Initialize cipher with key from env or file."""
        self.key_file = Path(
            key_file or os.environ.get(
                "NETAUDIT_KEY_FILE", self.DEFAULT_KEY_FILE
            )
        )

        logger.info("Initializing PasswordCipher with key file: %s",
                    self.key_file)

        self.key = self._load_key()
        self.fernet = Fernet(self.key)

    def _load_key(self) -> bytes:
        """Load Fernet key from environment variable or file."""
        env_key = os.environ.get(self.ENV_KEY_NAME)

        if env_key:
            return env_key.encode()

        if self.key_file.exists():
            return self.key_file.read_bytes()

        return self._generate_and_store_key()

    def _generate_and_store_key(self) -> bytes:
        """Generate and persist a new Fernet key."""
        key = Fernet.generate_key()

        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file.write_bytes(key)

        try:
            self.key_file.chmod(0o600)
        except PermissionError:
            logger.warning("Permission change failed for key file: %s",
                           self.key_file)

        return key

    def encrypt(self, plain_text: str) -> str:
        """Encrypt plain text using Fernet."""
        if not plain_text:
            return ""

        return self.fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        """Decrypt cipher text using Fernet."""
        if not cipher_text:
            return ""

        try:
            return self.fernet.decrypt(cipher_text.encode()).decode()
        except InvalidToken:
            raise ValueError(
                "Decryption failed: invalid key or corrupted data."
            )
