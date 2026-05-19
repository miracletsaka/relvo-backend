"""create template_segments table

Revision ID: create_template_segments
Revises:
Create Date: 2026-05-15

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "create_template_segments"
down_revision = "653e612fa084"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "template_segments",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),

        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            "template_family",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "segment_key",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=200),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "shapes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),

        sa.Column(
            "canvas_width",
            sa.Integer(),
            nullable=False,
            server_default="1080",
        ),

        sa.Column(
            "canvas_height",
            sa.Integer(),
            nullable=False,
            server_default="1350",
        ),

        sa.Column(
            "compatible_tones",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),

        sa.Column(
            "compatible_categories",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),

        sa.Column(
            "preview_url",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "thumbnail_url",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "generation_source",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),

        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),

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

        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organisations.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_template_segments_org_id",
        "template_segments",
        ["org_id"],
    )

    op.create_index(
        "ix_template_segments_template_family",
        "template_segments",
        ["template_family"],
    )

    op.create_index(
        "ix_template_segments_segment_key",
        "template_segments",
        ["segment_key"],
    )


def downgrade():
    op.drop_index("ix_template_segments_segment_key")
    op.drop_index("ix_template_segments_template_family")
    op.drop_index("ix_template_segments_org_id")

    op.drop_table("template_segments")