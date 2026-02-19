"""
api/routes_financial.py — Financial ID API Endpoints

Endpoints:
    POST /financial/{citizen_id}/records   → Add financial record
    GET  /financial/{citizen_id}/records   → Get financial records
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from db.session import get_db
from modules.financial import create_financial_record, get_financial_records

router = APIRouter()


class FinancialRecordRequest(BaseModel):
    requester_id: str
    pan_hash: str
    financial_year: str         # e.g. "2024-25"
    record_type: str            # itr | tds | gst | credit_score
    data: dict
    total_income: Optional[float] = None
    tax_paid: Optional[float] = None


@router.post("/{citizen_id}/records", status_code=201)
async def add_financial_record(
    citizen_id: str,
    body: FinancialRecordRequest,
    db: AsyncSession = Depends(get_db),
):
    return await create_financial_record(
        db=db,
        citizen_id=citizen_id,
        requester_id=body.requester_id,
        pan_hash=body.pan_hash,
        financial_year=body.financial_year,
        record_type=body.record_type,
        data=body.data,
        total_income=body.total_income,
        tax_paid=body.tax_paid,
    )


@router.get("/{citizen_id}/records")
async def list_financial_records(
    citizen_id: str,
    requester_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await get_financial_records(db, citizen_id, requester_id)
