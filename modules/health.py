"""
modules/health.py — Health Records Module
==========================================
Business logic for creating, reading, and sharing health records.
All data is encrypted before DB storage and logged to the blockchain.

Flow:
    API route → check consent → encrypt data → save DB → write block → return
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.crypto import crypto_engine
from core.blockchain import blockchain
from core.consent import require_permission
from db.models import HealthRecord, ConsentRecord, AuditLog

logger = logging.getLogger("bharatchain.modules.health")


async def create_health_record(
    db: AsyncSession,
    citizen_id: str,
    requester_id: str,
    record_type: str,
    provider_name: str,
    provider_id: str,
    record_data: dict,
    record_date: datetime = None,
) -> dict:
    """
    Save a new health record for a citizen.
    Only the citizen themselves or a consented provider can do this.
    """
    # 1. Check consent
    consents = await _get_active_consents(db, citizen_id)
    require_permission(citizen_id, requester_id, "health", consents)

    # 2. Encrypt sensitive data
    encrypted_data = crypto_engine.encrypt_dict(record_data)

    # 3. Save to DB
    record = HealthRecord(
        citizen_id=citizen_id,
        record_type=record_type,
        provider_name=provider_name,
        provider_id=provider_id,
        data_encrypted=encrypted_data,
        record_date=record_date or datetime.utcnow(),
    )
    db.add(record)
    await db.flush()   # get the ID before commit

    # 4. Write to blockchain
    block = await blockchain.write_block("HEALTH_RECORD", {
        "event": "HEALTH_RECORD_CREATED",
        "citizen_id": citizen_id,
        "record_id": record.id,
        "record_type": record_type,
        "provider_id": provider_id,
        "timestamp": datetime.utcnow().isoformat(),
    })
    record.block_hash = block["hash"]

    # 5. Audit log
    await _write_audit(db, citizen_id, requester_id, provider_name, "WRITE", "health", f"Created {record_type}")
    await db.commit()

    logger.info(f"Health record created for citizen {citizen_id} by {provider_name}")
    return {"record_id": record.id, "block_hash": block["hash"], "status": "created"}


async def get_health_records(
    db: AsyncSession,
    citizen_id: str,
    requester_id: str,
    requester_name: str = "",
) -> list:
    """Retrieve all health records for a citizen (if permitted)."""
    consents = await _get_active_consents(db, citizen_id)
    require_permission(citizen_id, requester_id, "health", consents)

    result = await db.execute(
        select(HealthRecord).where(HealthRecord.citizen_id == citizen_id)
    )
    records = result.scalars().all()

    # Decrypt and return
    decrypted = []
    for r in records:
        decrypted.append({
            "id": r.id,
            "record_type": r.record_type,
            "provider_name": r.provider_name,
            "record_date": r.record_date.isoformat(),
            "data": crypto_engine.decrypt_dict(r.data_encrypted),
            "block_hash": r.block_hash,
        })

    await _write_audit(db, citizen_id, requester_id, requester_name, "READ", "health", f"Read {len(records)} records")
    return decrypted


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_active_consents(db: AsyncSession, citizen_id: str) -> list:
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.citizen_id == citizen_id,
            ConsentRecord.is_active == True,
        )
    )
    return result.scalars().all()


async def _write_audit(db, citizen_id, actor_id, actor_name, action, module, details):
    log = AuditLog(
        citizen_id=citizen_id,
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        module=module,
        details=details,
    )
    db.add(log)
