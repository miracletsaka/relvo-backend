"""Add voice settings for Retell outbound calling."""

from alembic import op
import sqlalchemy as sa

revision = "voice_settings_001"
down_revision = "facebook_oauth_001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "voice_settings",
        sa.Column(
            "org_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("retell_api_key_enc", sa.Text(), nullable=True),
        sa.Column("retell_agent_id", sa.Text(), nullable=True),
        sa.Column("from_number", sa.Text(), nullable=True),
        sa.Column("pitch", sa.Text(), nullable=True),
        sa.Column("test_mode", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("test_numbers", sa.Text(), nullable=True),
        sa.Column("calling_start", sa.Text(), nullable=False, server_default="09:00"),
        sa.Column("calling_end", sa.Text(), nullable=False, server_default="17:00"),
        sa.Column("max_calls_per_run", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("voice_settings")