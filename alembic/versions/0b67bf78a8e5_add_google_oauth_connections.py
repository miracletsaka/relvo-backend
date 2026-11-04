
"""Add Google OAuth connection and state tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# Replace this with the revision ID of the migration
# immediately preceding this new migration.
revision = "google_oauth_001"
down_revision = "0830def5020b"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "google_oauth_states" not in existing_tables:
        op.create_table(
            "google_oauth_states",
            sa.Column("state", sa.String(), primary_key=True),
            sa.Column(
                "org_id",
                postgresql.UUID(as_uuid=False),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=False),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "google_connections" not in existing_tables:
        op.create_table(
            "google_connections",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=False),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "org_id",
                postgresql.UUID(as_uuid=False),
                nullable=False,
            ),
            sa.Column(
                "connected_by_user_id",
                postgresql.UUID(as_uuid=False),
                nullable=False,
            ),
            sa.Column("google_email", sa.String(), nullable=True),
            sa.Column("access_token_encrypted", sa.Text(), nullable=False),
            sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
            sa.Column("scopes", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

        op.create_index(
            "ix_google_connections_org_id",
            "google_connections",
            ["org_id"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "google_connections" in existing_tables:
        op.drop_table("google_connections")

    if "google_oauth_states" in existing_tables:
        op.drop_table("google_oauth_states")
