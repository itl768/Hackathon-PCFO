from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now_utc() -> datetime:
    return datetime.now(UTC)


class InvoiceRecord(Base):
    __tablename__ = "invoice"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="received")
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_uri: Mapped[str] = mapped_column(String(1024), nullable=False)

    extracted_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duplicate_of: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("invoice.id"), nullable=True
    )
    agent_outputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc
    )

    line_items: Mapped[list[LineItemRecord]] = relationship(
        "LineItemRecord",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="LineItemRecord.position",
    )
    findings: Mapped[list[FindingRecord]] = relationship(
        "FindingRecord",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="FindingRecord.created_at",
    )

    __table_args__ = (
        Index(
            "ix_invoice_natural_key",
            "status",
        ),
    )


class LineItemRecord(Base):
    __tablename__ = "line_item"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))


class FindingRecord(Base):
    __tablename__ = "finding"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    field_path: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_agent: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )


class AgentRunRecord(Base):
    __tablename__ = "agent_run"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    output_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class InvoiceEventRecord(Base):
    __tablename__ = "invoice_event"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
