"""
api/routes_assets.py — Capital Assets API Endpoints

Endpoints:
    POST /assets/{citizen_id}/sync   → Sync asset portfolio
    GET  /assets/{citizen_id}        → Get all asset records
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from db.session import get_db
from modules.assets import sync_assets, get_assets

router = APIRouter()


class AssetSyncRequest(BaseModel):
    requester_id: str
    asset_type: str             # equity | mf | gold | fd | crypto
    source: str                 # CDSL | NSDL | AMFI | bank_name
    portfolio_data: dict
    net_value: float
    ltcg: Optional[float] = 0.0
    stcg: Optional[float] = 0.0


@router.post("/{citizen_id}/sync", status_code=201)
async def sync_asset_portfolio(
    citizen_id: str,
    body: AssetSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    return await sync_assets(
        db=db,
        citizen_id=citizen_id,
        requester_id=body.requester_id,
        asset_type=body.asset_type,
        source=body.source,
        portfolio_data=body.portfolio_data,
        net_value=body.net_value,
        ltcg=body.ltcg,
        stcg=body.stcg,
    )


@router.get("/{citizen_id}")
async def list_assets(
    citizen_id: str,
    requester_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await get_assets(db, citizen_id, requester_id)
