"""
core/crypto.py — Cryptography Engine
======================================
Central place for ALL encryption, hashing, and ZK-proof operations.
Every module imports from here — never roll your own crypto elsewhere.

Provides:
- AES-256 encryption / decryption  (via Fernet)
- SHA-3 / Keccak-256 hashing       (for biometrics, UIDs)
- JWT token creation / verification
- ZK-proof stubs                   (placeholder for snarkjs integration)
"""

import hashlib
import hmac
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from config import settings

logger = logging.getLogger("bharatchain.crypto")


class CryptoEngine:
    """
    Singleton crypto engine — initialized once in main.py,
    then used across all modules via:  from core.crypto import crypto_engine
    """

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._ready = False

    def initialize(self):
        """Called once on app startup (main.py lifespan)."""
        if not settings.ENCRYPTION_KEY:
            raise ValueError(
                "ENCRYPTION_KEY is not set in .env! "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        self._fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        self._ready = True
        logger.info("Crypto engine initialized.")

    def is_ready(self) -> str:
        return "ok" if self._ready else "not initialized"

    # ── Encryption ─────────────────────────────────────────────────────────
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypts a string using AES-256 (Fernet).
        Returns base64-encoded ciphertext safe to store in DB.
        """
        if not self._ready:
            raise RuntimeError("CryptoEngine not initialized. Call initialize() first.")
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts a previously encrypted string."""
        if not self._ready:
            raise RuntimeError("CryptoEngine not initialized.")
        return self._fernet.decrypt(ciphertext.encode()).decode()

    def encrypt_dict(self, data: dict) -> str:
        """Encrypts an entire dict (serializes to JSON first)."""
        import json
        return self.encrypt(json.dumps(data))

    def decrypt_dict(self, ciphertext: str) -> dict:
        """Decrypts and deserializes a dict."""
        import json
        return json.loads(self.decrypt(ciphertext))

    # ── Hashing ────────────────────────────────────────────────────────────
    def hash_sha3(self, data: str) -> str:
        """
        SHA-3 (Keccak-256) hash — used for biometric hashes, UIDs.
        One-way: you can verify but never reverse.
        """
        return hashlib.sha3_256(data.encode()).hexdigest()

    def hash_biometric(self, raw_biometric_bytes: bytes, salt: str) -> str:
        """
        Hashes raw biometric data (fingerprint/iris bytes) with PBKDF2.
        The salt should be the citizen's UID hash — unique per person.
        Raw biometric NEVER stored — only this hash.
        """
        key = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=raw_biometric_bytes,
            salt=salt.encode(),
            iterations=settings.BIOMETRIC_HASH_ITERATIONS,
        )
        return base64.b64encode(key).decode()

    def verify_biometric(self, raw_biometric_bytes: bytes, salt: str, stored_hash: str) -> bool:
        """Verify a biometric against its stored hash."""
        computed = self.hash_biometric(raw_biometric_bytes, salt)
        return hmac.compare_digest(computed, stored_hash)

    def hash_uid(self, uid: str) -> str:
        """Hash an Aadhaar UID — we never store raw UIDs."""
        return self.hash_sha3(uid + settings.JWT_SECRET_KEY)  # salted

    # ── JWT Tokens ─────────────────────────────────────────────────────────
    def create_access_token(self, subject: str, extra_data: dict = None) -> str:
        """
        Create a signed JWT token for a citizen.
        subject = citizen DID or ID.
        """
        payload = {
            "sub": subject,
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES),
            "iat": datetime.utcnow(),
        }
        if extra_data:
            payload.update(extra_data)
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def verify_token(self, token: str) -> dict:
        """Verify and decode a JWT. Raises JWTError if invalid/expired."""
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    # ── ZK Proofs (Stubs) ──────────────────────────────────────────────────
    def generate_zk_proof(self, claim: str, private_data: Any) -> dict:
        """
        Zero-Knowledge Proof stub.
        In production: call snarkjs or py_ecc to generate a real Groth16 proof.
        For now: returns a simulated proof structure.

        Example claims:
            "age_over_18"   → proves citizen is adult without revealing DOB
            "income_above"  → proves income > threshold without revealing amount
            "is_citizen"    → proves citizenship without revealing UID
        """
        logger.info(f"Generating ZK proof for claim: {claim}")
        proof_hash = self.hash_sha3(f"{claim}:{str(private_data)}")
        return {
            "claim": claim,
            "proof": proof_hash[:64],           # simulated proof
            "public_inputs": [claim],
            "verified": True,
            "proof_type": "groth16_stub",       # replace with real snarkjs call
            "generated_at": datetime.utcnow().isoformat(),
        }

    def verify_zk_proof(self, proof: dict, claim: str) -> bool:
        """Verify a ZK proof for a claim. Stub — always True for simulation."""
        return proof.get("claim") == claim and proof.get("verified") is True


# Singleton instance — import this everywhere
crypto_engine = CryptoEngine()
