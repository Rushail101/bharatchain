"""
modules/property.py — Land & Property Registry Module
=======================================================
Handles immutable land title storage, transfer, and verification.
"""

import uuid
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.crypto import crypto_engine
from core.blockchain import blockchain
from core.consent import require_permission
from db.models import PropertyRecord, ConsentRecord, AuditLog

logger = logging.getLogger("bharatchain.modules.property")


async def register_property(
    db: AsyncSession,
    citizen_id: str,
    requester_id: str,
    property_type: str,
    state: str,
    district: str,
    area_sqft: float,
    registered_value: float,
    registration_date: datetime,
    document_data: dict = None,
) -> dict:
    """Register a new property title on the blockchain."""
    consents = await _get_active_consents(db, citizen_id)
    require_permission(citizen_id, requester_id, "property", consents)

    property_uid = f"PROP-{state.upper()[:2]}-{str(uuid.uuid4())[:8].upper()}"

    record = PropertyRecord(
        citizen_id=citizen_id,
        property_uid=property_uid,
        property_type=property_type,
        state=state,
        district=district,
        area_sqft=area_sqft,
        registered_value_encrypted=crypto_engine.encrypt(str(registered_value)),
        registration_date=registration_date,
        encumbrance_status="clear",
    )
    db.add(record)
    await db.flush()

    block = await blockchain.write_block("PROPERTY_TITLE", {
        "event": "PROPERTY_REGISTERED",
        "citizen_id": citizen_id,
        "property_uid": property_uid,
        "property_type": property_type,
        "state": state,
        "district": district,
        "timestamp": datetime.utcnow().isoformat(),
    })
    record.block_hash = block["hash"]

    db.add(AuditLog(citizen_id=citizen_id, actor_id=requester_id,
                    action="WRITE", module="property", details=f"Registered {property_uid}"))
    await db.commit()
    return {"property_uid": property_uid, "block_hash": block["hash"], "status": "registered"}


async def get_properties(db: AsyncSession, citizen_id: str, requester_id: str) -> list:
    """Retrieve all property records for a citizen."""
    consents = await _get_active_consents(db, citizen_id)
    require_permission(citizen_id, requester_id, "property", consents)

    result = await db.execute(
        select(PropertyRecord).where(PropertyRecord.citizen_id == citizen_id)
    )
    records = result.scalars().all()

    properties = []
    for r in records:
        properties.append({
            "id": r.id,
            "property_uid": r.property_uid,
            "property_type": r.property_type,
            "state": r.state,
            "district": r.district,
            "area_sqft": r.area_sqft,
            "registered_value": crypto_engine.decrypt(r.registered_value_encrypted),
            "registration_date": r.registration_date.isoformat(),
            "encumbrance_status": r.encumbrance_status,
            "block_hash": r.block_hash,
        })

    db.add(AuditLog(citizen_id=citizen_id, actor_id=requester_id,
                    action="READ", module="property", details=f"Read {len(records)} properties"))
    return properties


async def _get_active_consents(db: AsyncSession, citizen_id: str) -> list:
    result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.citizen_id == citizen_id, ConsentRecord.is_active == True)
    )
    return result.scalars().all()
