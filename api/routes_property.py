"""
api/routes_property.py — Property Registry API Endpoints

Endpoints:
    POST /property/{citizen_id}/register   → Register a property title
    GET  /property/{citizen_id}/titles     → Get all property titles
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from db.session import get_db
from modules.property import register_property, get_properties

router = APIRouter()


class PropertyRequest(BaseModel):
    requester_id: str
    property_type: str          # flat | plot | agricultural | commercial
    state: str
    district: str
    area_sqft: float
    registered_value: float
    registration_date: str      # ISO format
    document_data: Optional[dict] = None


@router.post("/{citizen_id}/register", status_code=201)
async def register_property_title(
    citizen_id: str,
    body: PropertyRequest,
    db: AsyncSession = Depends(get_db),
):
    return await register_property(
        db=db,
        citizen_id=citizen_id,
        requester_id=body.requester_id,
        property_type=body.property_type,
        state=body.state,
        district=body.district,
        area_sqft=body.area_sqft,
        registered_value=body.registered_value,
        registration_date=datetime.fromisoformat(body.registration_date),
        document_data=body.document_data,
    )


@router.get("/{citizen_id}/titles")
async def list_properties(
    citizen_id: str,
    requester_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await get_properties(db, citizen_id, requester_id)
