"""outbound calling tables

Creates: voice_settings, outbound_calls.
Safe to run even if a table already exists (it is skipped).

Revision ID: 9b2e4d6a1c58
Revises: REPLACE_WITH_CURRENT_HEAD
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Run `alembic heads` and paste the id it prints into down_revision below.
revision = "9b2e4d6a1c58"
down_revision = "voice_settings_001"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
UUID_DEFAULT = sa.text("gen_random_uuid()")


def _has(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    # ── Voice agent settings (one row per organisation) ──
    if not _has("voice_settings"):
        op.create_table(
            "voice_settings",
            sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
            sa.Column("org_id", UUID, sa.ForeignKey("organisations.id", ondelete="CASCADE"),
                      nullable=False, unique=True),
            sa.Column("retell_api_key_enc", sa.Text(), nullable=True),     # encrypted, never returned to the browser
            sa.Column("retell_agent_id", sa.String(200), nullable=True),
            sa.Column("from_number", sa.String(20), nullable=True),        # E.164, e.g. +14155550123
            sa.Column("pitch", sa.Text(), nullable=True),
            sa.Column("test_mode", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("test_numbers", sa.Text(), nullable=False, server_default=""),  # comma separated E.164
            sa.Column("calling_start", sa.String(5), nullable=False, server_default="09:00"),
            sa.Column("calling_end", sa.String(5), nullable=False, server_default="17:00"),
            sa.Column("max_calls_per_run", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        )

    # ── Outbound calls (one row per call) ──
    if not _has("outbound_calls"):
        op.create_table(
            "outbound_calls",
            sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
            sa.Column("org_id", UUID, sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
            # the registered business that was called
            sa.Column("lead_org_id", UUID, sa.ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True),
            sa.Column("business_name", sa.Text(), nullable=True),
            sa.Column("lead_phone", sa.String(20), nullable=False),        # the business's real number
            sa.Column("dialed_number", sa.String(20), nullable=False),     # who was dialed (a test number in test mode)
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("website", sa.Text(), nullable=True),
            sa.Column("test_redirect", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("retell_call_id", sa.Text(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="initiated"),  # initiated | registered | failed | ended
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),                # filled by the webhook (Phase 3)
            sa.Column("qualified", sa.Boolean(), nullable=True),           # filled by the webhook (Phase 3)
            sa.Column("analysis", postgresql.JSONB(), nullable=True),      # filled by the webhook (Phase 3)
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        )
        op.create_index("ix_outbound_calls_org_created", "outbound_calls", ["org_id", sa.text("created_at DESC")])
        op.create_index("ix_outbound_calls_lead_phone", "outbound_calls", ["lead_phone"])
        op.create_index("ix_outbound_calls_retell_call_id", "outbound_calls", ["retell_call_id"])


def downgrade() -> None:
    for table in ("outbound_calls", "voice_settings"):
        if _has(table):
            op.drop_table(table)