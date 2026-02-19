"""
api/routes_health.py — Health Records API Endpoints

Endpoints:
    POST /health/{citizen_id}/records     → Add a health record
    GET  /health/{citizen_id}/records     → Get all health records
"""

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from db.session import get_db
from modules.health import create_health_record, get_health_records

router = APIRouter()


class HealthRecordRequest(BaseModel):
    requester_id: str           # e.g. "APOLLO_HOSPITAL"
    record_type: str            # prescription | diagnosis | vaccination | surgery
    provider_name: str
    provider_id: str
    record_data: dict           # FHIR R4 compliant dict
    record_date: Optional[str] = None


@router.post("/{citizen_id}/records", status_code=201)
async def add_health_record(
    citizen_id: str,
    body: HealthRecordRequest,
    db: AsyncSession = Depends(get_db),
):
    record_date = datetime.fromisoformat(body.record_date) if body.record_date else None
    return await create_health_record(
        db=db,
        citizen_id=citizen_id,
        requester_id=body.requester_id,
        record_type=body.record_type,
        provider_name=body.provider_name,
        provider_id=body.provider_id,
        record_data=body.record_data,
        record_date=record_date,
    )


@router.get("/{citizen_id}/records")
async def list_health_records(
    citizen_id: str,
    requester_id: str,
    requester_name: str = "",
    db: AsyncSession = Depends(get_db),
):
    return await get_health_records(db, citizen_id, requester_id, requester_name)
