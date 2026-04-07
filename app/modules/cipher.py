"""
PasswordCipher Module

This module provides functionality to encrypt and decrypt passwords
using the Fernet symmetric encryption from the cryptography library.

"""

from cryptography.fernet import Fernet, InvalidToken
from pathlib import Path
import os

class PasswordCipher:
    """
    A class to handle encryption and decryption of passwords using Fernet symmetric encryption.

    Attributes:
        key_file (Path): The path to the file storing the Fernet key.
        fernet (Fernet): The Fernet instance for encryption and decryption.
    """
    ENV_KEY_NAME = "NETAUDIT_FERNET_KEY"
    DEFAULT_KEY_FILE = "secrets/fernet.key"

    def __init__(self, key_file: str | None = None):
        self.key_file = Path(
            key_file or os.environ.get("NETAUDIT_KEY_FILE", self.DEFAULT_KEY_FILE)
        )

        self.key = self._load_key()
        self.fernet = Fernet(self.key)

    def _load_key(self) -> bytes:
        """
        Loads the Fernet key from an environment variable or a file.

        Returns:
            The Fernet key as bytes.
        """
        env_key = os.environ.get(self.ENV_KEY_NAME)
        if env_key:
            return env_key.encode()

        if self.key_file.exists():
            return self.key_file.read_bytes()

        return self._generate_and_store_key()

    def _generate_and_store_key(self) -> bytes:
        """
        Generates a new Fernet key and stores it in the specified key file.

        Returns:
            The generated Fernet key as bytes.
        """
        key = Fernet.generate_key()

        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file.write_bytes(key)

        try:
            self.key_file.chmod(0o600)
        except PermissionError:
            pass

        return key

    def encrypt(self, plain_text: str) -> str:
        """
        Encrypts the given plain text using Fernet symmetric encryption.
        Args:
            plain_text: The plain text string to be encrypted.

        Returns:
            The encrypted string (cipher text).
        """
        if not plain_text:
            return ""
        return self.fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        """
        Decrypts the given cipher text using Fernet symmetric encryption.
        Args:
            cipher_text: The encrypted string to be decrypted.

        Returns:
            The decrypted plain text string.
        """
        if not cipher_text:
            return ""
        try:
            return self.fernet.decrypt(cipher_text.encode()).decode()
        except InvalidToken:
            raise ValueError("Decryption failed: invalid key or corrupted data.")
