"""
core/consent.py — Consent & Permission Engine
===============================================
The security gate. Called by EVERY module before any data access.
If this says NO, data is never touched — period.

Access Tiers:
    TIER 1 — government:   UIDAI, Income Tax, Courts (broad access, always audited)
    TIER 2 — regulated:    Banks, Hospitals, Insurance (consent required, scoped)
    TIER 3 — commercial:   Apps, fintechs (ZK-proofs only, no raw data)
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, status

logger = logging.getLogger("bharatchain.consent")

# Tier 1 requester IDs — government bodies with elevated (but still audited) access
GOVERNMENT_ENTITIES = {
    "UIDAI", "INCOME_TAX_DEPT", "SUPREME_COURT", "HIGH_COURT",
    "DISTRICT_COURT", "CBI", "ED", "SEBI", "RBI", "ELECTION_COMMISSION",
    "MCA", "GST_COUNCIL", "SUBREGISTRAR_OFFICE",
}


def get_requester_tier(requester_id: str) -> str:
    """Determine which access tier a requester belongs to."""
    if requester_id.upper() in GOVERNMENT_ENTITIES:
        return "government"
    # In production: look up a verified registry of banks/hospitals
    # For now: anything with BANK, HOSPITAL, INSURANCE in the ID = regulated
    rid = requester_id.upper()
    if any(keyword in rid for keyword in ["BANK", "HOSPITAL", "INSURANCE", "NBFC", "CLINIC"]):
        return "regulated"
    return "commercial"


def check_permission(
    citizen_id: str,
    requester_id: str,
    module: str,
    active_consents: list,   # list of ConsentRecord objects from DB
) -> bool:
    """
    Core permission check. Returns True if access is permitted.

    Rules:
    - Government tier: always permitted (but logged)
    - Regulated tier: permitted only if active consent exists for the module
    - Commercial tier: NEVER gets raw data (only ZK-proofs via separate endpoint)
    """
    tier = get_requester_tier(requester_id)

    if tier == "government":
        logger.info(f"GOVERNMENT access granted: {requester_id} → {module} for {citizen_id}")
        return True

    if tier == "regulated":
        for consent in active_consents:
            if (
                consent.requester_id == requester_id
                and module in consent.modules_granted
                and consent.is_active
                and (consent.expires_at is None or consent.expires_at > datetime.utcnow())
            ):
                logger.info(f"REGULATED access granted: {requester_id} → {module} for {citizen_id}")
                return True
        logger.warning(f"REGULATED access DENIED: {requester_id} → {module} for {citizen_id} (no valid consent)")
        return False

    # Commercial tier — never raw data
    logger.warning(f"COMMERCIAL access DENIED: {requester_id} → {module} for {citizen_id}")
    return False


def require_permission(
    citizen_id: str,
    requester_id: str,
    module: str,
    active_consents: list,
):
    """
    Same as check_permission but raises HTTP 403 instead of returning False.
    Use this as a guard in route handlers:

        require_permission(citizen_id, requester_id, "health", consents)
        # execution continues only if permitted
    """
    if not check_permission(citizen_id, requester_id, module, active_consents):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to module '{module}' denied for requester '{requester_id}'. "
                   "Ensure the citizen has granted consent.",
        )


def build_consent_block_data(
    citizen_id: str,
    requester_id: str,
    modules: list,
    action: str = "GRANTED",
) -> dict:
    """Data written to the blockchain when consent is granted or revoked."""
    return {
        "event": f"CONSENT_{action}",
        "citizen_id": citizen_id,
        "requester_id": requester_id,
        "modules": modules,
        "timestamp": datetime.utcnow().isoformat(),
    }
