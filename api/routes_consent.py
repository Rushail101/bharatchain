"""
api/routes_consent.py — Consent Management API Endpoints

Endpoints:
    POST /consent/{citizen_id}/grant    → Grant access to a requester
    POST /consent/{citizen_id}/revoke   → Revoke access
    GET  /consent/{citizen_id}          → List all active consents
    GET  /consent/{citizen_id}/audit    → View full audit trail
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import List, Optional

from db.session import get_db
from db.models import ConsentRecord, AuditLog
from core.blockchain import blockchain
from core.consent import build_consent_block_data
from config import settings

router = APIRouter()


class GrantConsentRequest(BaseModel):
    citizen_uid: str                    # must match registered UID to prove ownership
    requester_id: str
    requester_name: str
    modules: List[str]                  # ["health", "financial", "property", "assets"]
    duration_days: Optional[int] = 30


class RevokeConsentRequest(BaseModel):
    citizen_uid: str
    requester_id: str


@router.post("/{citizen_id}/grant", status_code=201)
async def grant_consent(
    citizen_id: str,
    body: GrantConsentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Citizen grants a requester access to specified modules."""
    # Validate modules
    valid_modules = {"health", "financial", "property", "assets", "identity"}
    invalid = set(body.modules) - valid_modules
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid modules: {invalid}")

    # Cap duration
    duration = min(body.duration_days, settings.MAX_CONSENT_DURATION_DAYS)
    expires_at = datetime.utcnow() + timedelta(days=duration)

    # Deactivate any existing consent from same requester
    existing = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.citizen_id == citizen_id,
            ConsentRecord.requester_id == body.requester_id,
            ConsentRecord.is_active == True,
        )
    )
    for old in existing.scalars().all():
        old.is_active = False

    # Create new consent
    from core.consent import get_requester_tier
    consent = ConsentRecord(
        citizen_id=citizen_id,
        requester_id=body.requester_id,
        requester_name=body.requester_name,
        requester_tier=get_requester_tier(body.requester_id),
        modules_granted=body.modules,
        expires_at=expires_at,
    )
    db.add(consent)
    await db.flush()

    # Write to blockchain
    block = await blockchain.write_block(
        "CONSENT",
        build_consent_block_data(citizen_id, body.requester_id, body.modules, "GRANTED")
    )
    consent.block_hash = block["hash"]

    db.add(AuditLog(
        citizen_id=citizen_id, actor_id="CITIZEN", actor_name="Citizen",
        action="CONSENT_GRANTED", module="consent",
        details=f"Granted {body.requester_id} access to {body.modules} for {duration} days"
    ))
    await db.commit()

    return {
        "consent_id": consent.id,
        "requester_id": body.requester_id,
        "modules": body.modules,
        "expires_at": expires_at.isoformat(),
        "block_hash": block["hash"],
        "status": "granted",
    }


@router.post("/{citizen_id}/revoke")
async def revoke_consent(
    citizen_id: str,
    body: RevokeConsentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Citizen revokes a requester's access."""
    existing = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.citizen_id == citizen_id,
            ConsentRecord.requester_id == body.requester_id,
            ConsentRecord.is_active == True,
        )
    )
    consents = existing.scalars().all()
    if not consents:
        raise HTTPException(status_code=404, detail="No active consent found for this requester.")

    for c in consents:
        c.is_active = False

    block = await blockchain.write_block(
        "CONSENT",
        build_consent_block_data(citizen_id, body.requester_id, [], "REVOKED")
    )
    db.add(AuditLog(
        citizen_id=citizen_id, actor_id="CITIZEN", actor_name="Citizen",
        action="CONSENT_REVOKED", module="consent",
        details=f"Revoked {body.requester_id} access"
    ))
    await db.commit()
    return {"status": "revoked", "block_hash": block["hash"]}


@router.get("/{citizen_id}")
async def list_consents(citizen_id: str, db: AsyncSession = Depends(get_db)):
    """List all active consents for a citizen."""
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.citizen_id == citizen_id,
            ConsentRecord.is_active == True,
        )
    )
    consents = result.scalars().all()
    return [
        {
            "id": c.id,
            "requester_id": c.requester_id,
            "requester_name": c.requester_name,
            "tier": c.requester_tier,
            "modules": c.modules_granted,
            "expires_at": c.expires_at.isoformat() if c.expires_at else "never",
            "granted_at": c.granted_at.isoformat(),
        }
        for c in consents
    ]


@router.get("/{citizen_id}/audit")
async def get_audit_trail(
    citizen_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Return the full on-DB audit trail for a citizen."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.citizen_id == citizen_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "actor": log.actor_name or log.actor_id,
            "action": log.action,
            "module": log.module,
            "details": log.details,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]
