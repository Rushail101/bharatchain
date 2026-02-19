"""
api/routes_identity.py — Identity API Endpoints
=================================================
Handles citizen registration, DID lookup, and biometric enrollment.

Endpoints:
    POST /identity/register        → Create new citizen identity
    GET  /identity/{citizen_id}    → Lookup identity by ID
    POST /identity/verify-biometric → Verify a biometric claim
    GET  /identity/{citizen_id}/did → Get DID for a citizen
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from db.session import get_db
from db.models import CitizenIdentity, AuditLog
from core.crypto import crypto_engine
from core.blockchain import blockchain
from core.identity import generate_did, build_identity_block_data

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    uid: str            # Aadhaar UID (will be hashed immediately, never stored raw)
    full_name: str
    dob: str            # "YYYY-MM-DD"
    gender: str = ""
    address: str = ""


class RegisterResponse(BaseModel):
    citizen_id: str
    did: str
    block_hash: str
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register_citizen(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new citizen on BharatChain.
    The UID is immediately hashed — raw UID never touches the DB.
    """
    # Hash the UID immediately
    uid_hash = crypto_engine.hash_uid(body.uid)

    # Check for duplicate
    existing = await db.execute(
        select(CitizenIdentity).where(CitizenIdentity.uid_hash == uid_hash)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="This UID is already registered.")

    # Generate DID
    did = generate_did(uid_hash)

    # Create DB record
    citizen = CitizenIdentity(
        did=did,
        uid_hash=uid_hash,
        full_name_encrypted=crypto_engine.encrypt(body.full_name),
        dob_encrypted=crypto_engine.encrypt(body.dob),
        gender_encrypted=crypto_engine.encrypt(body.gender) if body.gender else None,
        address_encrypted=crypto_engine.encrypt(body.address) if body.address else None,
    )
    db.add(citizen)
    await db.flush()

    # Write to blockchain
    block = await blockchain.write_block(
        "IDENTITY",
        build_identity_block_data(citizen.id, did, uid_hash)
    )
    citizen.block_hash = block["hash"]

    # Audit log
    db.add(AuditLog(
        citizen_id=citizen.id, actor_id="SELF", actor_name=body.full_name,
        action="WRITE", module="identity", details="Citizen registered"
    ))
    await db.commit()

    return RegisterResponse(
        citizen_id=citizen.id,
        did=did,
        block_hash=block["hash"],
        message="Identity registered successfully on BharatChain.",
    )


@router.get("/{citizen_id}")
async def get_identity(citizen_id: str, db: AsyncSession = Depends(get_db)):
    """Get public-safe identity info (no raw sensitive data returned)."""
    result = await db.execute(
        select(CitizenIdentity).where(CitizenIdentity.id == citizen_id)
    )
    citizen = result.scalars().first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found.")

    return {
        "citizen_id": citizen.id,
        "did": citizen.did,
        "block_hash": citizen.block_hash,
        "is_active": citizen.is_active,
        "created_at": citizen.created_at.isoformat(),
        "biometrics_enrolled": {
            "iris": citizen.iris_hash is not None,
            "fingerprint": citizen.fingerprint_hash is not None,
            "face": citizen.face_hash is not None,
        },
    }


@router.get("/{citizen_id}/did")
async def get_did(citizen_id: str, db: AsyncSession = Depends(get_db)):
    """Return the W3C DID document for a citizen."""
    result = await db.execute(
        select(CitizenIdentity).where(CitizenIdentity.id == citizen_id)
    )
    citizen = result.scalars().first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found.")

    # W3C DID Document format
    return {
        "@context": "https://www.w3.org/ns/did/v1",
        "id": citizen.did,
        "verificationMethod": [{
            "id": f"{citizen.did}#keys-1",
            "type": "EcdsaSecp256k1VerificationKey2019",
            "controller": citizen.did,
            "blockchainAccountId": citizen.block_hash,
        }],
        "authentication": [f"{citizen.did}#keys-1"],
    }
