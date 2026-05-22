"""invoicing initial schema

Revision ID: 0001_invoicing_initial
Revises:
Create Date: 2026-05-22

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_invoicing_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoice",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("document_uri", sa.String(length=1024), nullable=False),
        sa.Column("extracted_json", postgresql.JSONB(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("verdict", sa.String(length=32), nullable=True),
        sa.Column(
            "duplicate_of",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoice.id", name="fk_invoice_duplicate_of", use_alter=True),
            nullable=True,
        ),
        sa.Column(
            "agent_outputs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_invoice_sha256", "invoice", ["sha256"])
    op.create_index("ix_invoice_status", "invoice", ["status"])
    op.create_index(
        "ix_invoice_natural_key",
        "invoice",
        [
            sa.text("(extracted_json->>'vendor_name')"),
            sa.text("(extracted_json->>'invoice_number')"),
            sa.text("(extracted_json->>'invoice_date')"),
        ],
    )

    op.create_table(
        "line_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoice.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )
    op.create_index("ix_line_item_invoice_id", "line_item", ["invoice_id"])

    op.create_table(
        "finding",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoice.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("field_path", sa.String(length=256), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_agent", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_finding_invoice_id", "finding", ["invoice_id"])
    op.create_index("ix_finding_kind", "finding", ["kind"])

    op.create_table(
        "agent_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoice.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
        sa.Column("output_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
    )
    op.create_index("ix_agent_run_invoice_id", "agent_run", ["invoice_id"])

    op.create_table(
        "invoice_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoice.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_invoice_event_invoice_id", "invoice_event", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_invoice_event_invoice_id", table_name="invoice_event")
    op.drop_table("invoice_event")
    op.drop_index("ix_agent_run_invoice_id", table_name="agent_run")
    op.drop_table("agent_run")
    op.drop_index("ix_finding_kind", table_name="finding")
    op.drop_index("ix_finding_invoice_id", table_name="finding")
    op.drop_table("finding")
    op.drop_index("ix_line_item_invoice_id", table_name="line_item")
    op.drop_table("line_item")
    op.drop_index("ix_invoice_natural_key", table_name="invoice")
    op.drop_index("ix_invoice_status", table_name="invoice")
    op.drop_index("ix_invoice_sha256", table_name="invoice")
    op.drop_table("invoice")
