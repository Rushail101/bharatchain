"""
db/models.py — Database Table Definitions
==========================================
Each class = one table in PostgreSQL.
All sensitive fields are stored ENCRYPTED (handled by core/crypto.py before saving).
The blockchain stores hashes/proofs; the DB stores metadata and encrypted payloads.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from db.session import Base


def new_uuid():
    return str(uuid.uuid4())


# ── 1. Core Identity ──────────────────────────────────────────────────────────
class CitizenIdentity(Base):
    __tablename__ = "citizen_identities"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    did: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)   # W3C DID
    uid_hash: Mapped[str] = mapped_column(String(512), nullable=False)           # Aadhaar hash (not raw)
    full_name_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    dob_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    gender_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    address_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    iris_hash: Mapped[str] = mapped_column(String(512), nullable=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(512), nullable=True)
    face_hash: Mapped[str] = mapped_column(String(512), nullable=True)
    block_hash: Mapped[str] = mapped_column(String(512), nullable=True)          # chain reference
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    health_records: Mapped[list["HealthRecord"]] = relationship(back_populates="citizen")
    financial_records: Mapped[list["FinancialRecord"]] = relationship(back_populates="citizen")
    property_records: Mapped[list["PropertyRecord"]] = relationship(back_populates="citizen")
    asset_records: Mapped[list["AssetRecord"]] = relationship(back_populates="citizen")
    consents: Mapped[list["ConsentRecord"]] = relationship(back_populates="citizen")


# ── 2. Health Records ─────────────────────────────────────────────────────────
class HealthRecord(Base):
    __tablename__ = "health_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    citizen_id: Mapped[str] = mapped_column(ForeignKey("citizen_identities.id"), nullable=False)
    record_type: Mapped[str] = mapped_column(String(100))   # prescription | diagnosis | vaccination | surgery
    provider_name: Mapped[str] = mapped_column(String(255))
    provider_id: Mapped[str] = mapped_column(String(255))
    data_encrypted: Mapped[str] = mapped_column(Text)       # FHIR R4 JSON, encrypted
    ipfs_hash: Mapped[str] = mapped_column(String(255), nullable=True)   # large docs on IPFS
    block_hash: Mapped[str] = mapped_column(String(512), nullable=True)
    record_date: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    citizen: Mapped["CitizenIdentity"] = relationship(back_populates="health_records")


# ── 3. Financial Records ──────────────────────────────────────────────────────
class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    citizen_id: Mapped[str] = mapped_column(ForeignKey("citizen_identities.id"), nullable=False)
    pan_hash: Mapped[str] = mapped_column(String(512))       # hashed PAN, not raw
    financial_year: Mapped[str] = mapped_column(String(10))  # e.g. "2024-25"
    record_type: Mapped[str] = mapped_column(String(100))    # itr | tds | gst | credit_score
    data_encrypted: Mapped[str] = mapped_column(Text)
    total_income_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    tax_paid_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    block_hash: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    citizen: Mapped["CitizenIdentity"] = relationship(back_populates="financial_records")


# ── 4. Property Records ───────────────────────────────────────────────────────
class PropertyRecord(Base):
    __tablename__ = "property_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    citizen_id: Mapped[str] = mapped_column(ForeignKey("citizen_identities.id"), nullable=False)
    property_uid: Mapped[str] = mapped_column(String(255), unique=True)   # unique title ID on chain
    property_type: Mapped[str] = mapped_column(String(100))               # flat | plot | agricultural
    state: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(100))
    area_sqft: Mapped[float] = mapped_column(nullable=True)
    registered_value_encrypted: Mapped[str] = mapped_column(Text)
    registration_date: Mapped[datetime] = mapped_column(DateTime)
    encumbrance_status: Mapped[str] = mapped_column(String(50), default="clear")  # clear | mortgaged | disputed
    ipfs_hash: Mapped[str] = mapped_column(String(255), nullable=True)    # title deed document
    block_hash: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    citizen: Mapped["CitizenIdentity"] = relationship(back_populates="property_records")


# ── 5. Asset Records ──────────────────────────────────────────────────────────
class AssetRecord(Base):
    __tablename__ = "asset_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    citizen_id: Mapped[str] = mapped_column(ForeignKey("citizen_identities.id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(100))     # equity | mf | gold | fd | crypto
    source: Mapped[str] = mapped_column(String(100))         # CDSL | NSDL | AMFI | bank
    data_encrypted: Mapped[str] = mapped_column(Text)        # portfolio snapshot, encrypted
    net_value_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    ltcg_encrypted: Mapped[str] = mapped_column(Text, nullable=True)     # long-term capital gains
    stcg_encrypted: Mapped[str] = mapped_column(Text, nullable=True)     # short-term capital gains
    as_of_date: Mapped[datetime] = mapped_column(DateTime)
    block_hash: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    citizen: Mapped["CitizenIdentity"] = relationship(back_populates="asset_records")


# ── 6. Consent Records ────────────────────────────────────────────────────────
class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    citizen_id: Mapped[str] = mapped_column(ForeignKey("citizen_identities.id"), nullable=False)
    requester_id: Mapped[str] = mapped_column(String(255))       # e.g. "HDFC_BANK"
    requester_name: Mapped[str] = mapped_column(String(255))
    requester_tier: Mapped[str] = mapped_column(String(50))      # government | regulated | commercial
    modules_granted: Mapped[list] = mapped_column(JSON)          # ["health", "financial"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    block_hash: Mapped[str] = mapped_column(String(512), nullable=True)

    citizen: Mapped["CitizenIdentity"] = relationship(back_populates="consents")


# ── 7. Audit Log ──────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    citizen_id: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255))        # who accessed
    actor_name: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(100))          # READ | WRITE | VERIFY | DENIED
    module: Mapped[str] = mapped_column(String(100))          # health | financial | property etc.
    details: Mapped[str] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    block_hash: Mapped[str] = mapped_column(String(512), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
