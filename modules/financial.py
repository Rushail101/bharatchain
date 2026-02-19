"""
modules/financial.py — Financial ID Module (PAN+ Replacement)
===============================================================
Handles tax records, ITR filing data, credit scores, GST linkage.
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.crypto import crypto_engine
from core.blockchain import blockchain
from core.consent import require_permission
from db.models import FinancialRecord, ConsentRecord, AuditLog

logger = logging.getLogger("bharatchain.modules.financial")


async def create_financial_record(
    db: AsyncSession,
    citizen_id: str,
    requester_id: str,
    pan_hash: str,
    financial_year: str,
    record_type: str,
    data: dict,
    total_income: float = None,
    tax_paid: float = None,
) -> dict:
    """Save a financial record (ITR, TDS, GST, credit score, etc.)."""
    consents = await _get_active_consents(db, citizen_id)
    require_permission(citizen_id, requester_id, "financial", consents)

    record = FinancialRecord(
        citizen_id=citizen_id,
        pan_hash=pan_hash,
        financial_year=financial_year,
        record_type=record_type,
        data_encrypted=crypto_engine.encrypt_dict(data),
        total_income_encrypted=crypto_engine.encrypt(str(total_income)) if total_income else None,
        tax_paid_encrypted=crypto_engine.encrypt(str(tax_paid)) if tax_paid else None,
    )
    db.add(record)
    await db.flush()

    block = await blockchain.write_block("FINANCIAL_RECORD", {
        "event": "FINANCIAL_RECORD_CREATED",
        "citizen_id": citizen_id,
        "record_id": record.id,
        "record_type": record_type,
        "financial_year": financial_year,
        "timestamp": datetime.utcnow().isoformat(),
    })
    record.block_hash = block["hash"]

    db.add(AuditLog(citizen_id=citizen_id, actor_id=requester_id,
                    action="WRITE", module="financial", details=f"Created {record_type} for {financial_year}"))
    await db.commit()
    return {"record_id": record.id, "block_hash": block["hash"], "status": "created"}


async def get_financial_records(
    db: AsyncSession,
    citizen_id: str,
    requester_id: str,
) -> list:
    """Retrieve all financial records for a citizen (if permitted)."""
    consents = await _get_active_consents(db, citizen_id)
    require_permission(citizen_id, requester_id, "financial", consents)

    result = await db.execute(
        select(FinancialRecord).where(FinancialRecord.citizen_id == citizen_id)
    )
    records = result.scalars().all()

    decrypted = []
    for r in records:
        row = {
            "id": r.id,
            "financial_year": r.financial_year,
            "record_type": r.record_type,
            "data": crypto_engine.decrypt_dict(r.data_encrypted),
            "block_hash": r.block_hash,
        }
        if r.total_income_encrypted:
            row["total_income"] = crypto_engine.decrypt(r.total_income_encrypted)
        if r.tax_paid_encrypted:
            row["tax_paid"] = crypto_engine.decrypt(r.tax_paid_encrypted)
        decrypted.append(row)

    db.add(AuditLog(citizen_id=citizen_id, actor_id=requester_id,
                    action="READ", module="financial", details=f"Read {len(records)} records"))
    return decrypted


async def _get_active_consents(db: AsyncSession, citizen_id: str) -> list:
    result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.citizen_id == citizen_id, ConsentRecord.is_active == True)
    )
    return result.scalars().all()
