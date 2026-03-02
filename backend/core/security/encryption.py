"""
Credential encryption utilities using Fernet symmetric encryption.
"""

import base64
import hashlib

from cryptography.fernet import Fernet


class CredentialEncryption:
    """Handle encryption and decryption of sensitive credentials."""

    def __init__(self, secret_key: str):
        """
        Initialize with a secret key.

        Args:
            secret_key: Application secret key (will be hashed to 32 bytes for Fernet)
        """
        # Fernet requires a 32-byte base64-encoded key
        # Hash the secret key to ensure consistent 32-byte length
        key_bytes = hashlib.sha256(secret_key.encode()).digest()
        self.fernet = Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt(self, value: str) -> str:
        """
        Encrypt a string value.

        Args:
            value: Plain text value to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not value:
            return ""

        encrypted_bytes = self.fernet.encrypt(value.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted_value: str) -> str:
        """
        Decrypt an encrypted string value.

        Args:
            encrypted_value: Base64-encoded encrypted string

        Returns:
            Decrypted plain text value

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_value:
            return ""

        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_value.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt credential: {str(e)}")


# Singleton instance functions
def encrypt_credential(value: str, secret_key: str) -> str:
    """
    Encrypt a credential value.

    Args:
        value: Plain text credential
        secret_key: Application secret key

    Returns:
        Encrypted credential string
    """
    encryptor = CredentialEncryption(secret_key)
    return encryptor.encrypt(value)


def decrypt_credential(encrypted_value: str, secret_key: str) -> str:
    """
    Decrypt a credential value.

    Args:
        encrypted_value: Encrypted credential string
        secret_key: Application secret key

    Returns:
        Decrypted plain text credential

    Raises:
        ValueError: If decryption fails
    """
    encryptor = CredentialEncryption(secret_key)
    return encryptor.decrypt(encrypted_value)
