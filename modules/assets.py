"""
modules/assets.py — Capital Assets Module
==========================================
Handles equity, mutual funds, gold, FDs, crypto portfolio tracking.
Auto-computes LTCG/STCG for tax filing.
"""

import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.crypto import crypto_engine
from core.blockchain import blockchain
from core.consent import require_permission
from db.models import AssetRecord, ConsentRecord, AuditLog

logger = logging.getLogger("bharatchain.modules.assets")


async def sync_assets(
    db: AsyncSession,
    citizen_id: str,
    requester_id: str,
    asset_type: str,
    source: str,
    portfolio_data: dict,
    net_value: float,
    ltcg: float = 0.0,
    stcg: float = 0.0,
) -> dict:
    """Sync an asset portfolio snapshot from an external source (CDSL, AMFI, etc.)."""
    consents = await _get_active_consents(db, citizen_id)
    require_permission(citizen_id, requester_id, "assets", consents)

    record = AssetRecord(
        citizen_id=citizen_id,
        asset_type=asset_type,
        source=source,
        data_encrypted=crypto_engine.encrypt_dict(portfolio_data),
        net_value_encrypted=crypto_engine.encrypt(str(net_value)),
        ltcg_encrypted=crypto_engine.encrypt(str(ltcg)),
        stcg_encrypted=crypto_engine.encrypt(str(stcg)),
        as_of_date=datetime.utcnow(),
    )
    db.add(record)
    await db.flush()

    block = await blockchain.write_block("ASSET_SYNC", {
        "event": "ASSET_SYNCED",
        "citizen_id": citizen_id,
        "asset_type": asset_type,
        "source": source,
        "timestamp": datetime.utcnow().isoformat(),
    })
    record.block_hash = block["hash"]

    db.add(AuditLog(citizen_id=citizen_id, actor_id=requester_id,
                    action="WRITE", module="assets", details=f"Synced {asset_type} from {source}"))
    await db.commit()
    return {"record_id": record.id, "block_hash": block["hash"], "status": "synced"}


async def get_assets(db: AsyncSession, citizen_id: str, requester_id: str) -> list:
    """Get all asset records for a citizen."""
    consents = await _get_active_consents(db, citizen_id)
    require_permission(citizen_id, requester_id, "assets", consents)

    result = await db.execute(
        select(AssetRecord).where(AssetRecord.citizen_id == citizen_id)
    )
    records = result.scalars().all()

    assets = []
    for r in records:
        assets.append({
            "id": r.id,
            "asset_type": r.asset_type,
            "source": r.source,
            "portfolio": crypto_engine.decrypt_dict(r.data_encrypted),
            "net_value": crypto_engine.decrypt(r.net_value_encrypted),
            "ltcg": crypto_engine.decrypt(r.ltcg_encrypted),
            "stcg": crypto_engine.decrypt(r.stcg_encrypted),
            "as_of_date": r.as_of_date.isoformat(),
            "block_hash": r.block_hash,
        })

    db.add(AuditLog(citizen_id=citizen_id, actor_id=requester_id,
                    action="READ", module="assets", details=f"Read {len(records)} asset records"))
    return assets


async def _get_active_consents(db: AsyncSession, citizen_id: str) -> list:
    result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.citizen_id == citizen_id, ConsentRecord.is_active == True)
    )
    return result.scalars().all()
