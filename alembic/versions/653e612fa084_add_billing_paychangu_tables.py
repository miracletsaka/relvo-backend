"""add billing paychangu tables

Revision ID: 653e612fa084
Revises: 78803f398022
Create Date: 2026-04-26 15:51:00.736236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '653e612fa084'
down_revision: Union[str, Sequence[str], None] = '78803f398022'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "billing_payments",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),

        sa.Column("plan_id", sa.String(50), nullable=False),
        sa.Column("plan_name", sa.String(100), nullable=False),

        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="MWK"),

        sa.Column("provider", sa.String(50), nullable=False, server_default="paychangu"),
        sa.Column("payment_method", sa.String(50), nullable=False),

        sa.Column("mobile", sa.String(30), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),

        sa.Column("charge_id", sa.String(120), nullable=False, unique=True),
        sa.Column("provider_charge_id", sa.String(120)),
        sa.Column("provider_reference", sa.String(120)),

        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("failure_reason", sa.Text()),

        sa.Column("raw_initialize_response", sa.JSON()),
        sa.Column("raw_verify_response", sa.JSON()),
        sa.Column("raw_webhook_payload", sa.JSON()),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "billing_subscriptions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, unique=True),

        sa.Column("plan_id", sa.String(50), nullable=False, server_default="free"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),

        sa.Column("current_period_start", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),

        sa.Column("last_payment_id", sa.UUID(), sa.ForeignKey("billing_payments.id", ondelete="SET NULL")),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_table("billing_subscriptions")
    op.drop_table("billing_payments")