"""
core/identity.py — Decentralized Identity (DID) Management
============================================================
Handles W3C DID creation, biometric enrollment, and identity verification.
Called by modules/identity.py and api/routes_identity.py
"""

import uuid
import logging
from datetime import datetime
from core.crypto import crypto_engine

logger = logging.getLogger("bharatchain.identity")


def generate_did(uid_hash: str) -> str:
    """
    Generate a W3C-compliant Decentralized Identifier.
    Format: did:bharatchain:<unique-id>
    The UID hash is used as a seed so the same person always gets the same DID.
    """
    unique_part = crypto_engine.hash_sha3(uid_hash)[:32]
    return f"did:bharatchain:{unique_part}"


def enroll_biometrics(
    uid_hash: str,
    iris_bytes: bytes = None,
    fingerprint_bytes: bytes = None,
    face_bytes: bytes = None,
) -> dict:
    """
    Hash all provided biometrics using PBKDF2.
    Raw biometric bytes are discarded after hashing — never stored.

    Returns a dict of hashes safe to store in DB.
    """
    result = {}
    if iris_bytes:
        result["iris_hash"] = crypto_engine.hash_biometric(iris_bytes, uid_hash)
    if fingerprint_bytes:
        result["fingerprint_hash"] = crypto_engine.hash_biometric(fingerprint_bytes, uid_hash)
    if face_bytes:
        result["face_hash"] = crypto_engine.hash_biometric(face_bytes, uid_hash)
    return result


def verify_biometric_claim(
    raw_bytes: bytes,
    uid_hash: str,
    stored_hash: str,
) -> bool:
    """Verify a live biometric scan against its stored hash."""
    return crypto_engine.verify_biometric(raw_bytes, uid_hash, stored_hash)


def build_identity_block_data(citizen_id: str, did: str, uid_hash: str) -> dict:
    """Prepare the data dict to be written to the blockchain for a new identity."""
    return {
        "event": "IDENTITY_CREATED",
        "citizen_id": citizen_id,
        "did": did,
        "uid_hash": uid_hash,
        "timestamp": datetime.utcnow().isoformat(),
    }
