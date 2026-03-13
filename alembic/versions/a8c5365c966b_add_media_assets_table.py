"""add media_assets table

Revision ID: a8c5365c966b
Revises: 8d9d76f97264
Create Date: 2026-03-10 16:19:16.020015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8c5365c966b'
down_revision: Union[str, Sequence[str], None] = '8d9d76f97264'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('media_assets',
        sa.Column('brand_id', sa.String(), sa.ForeignKey('brands.id', ondelete='SET NULL'), nullable=True))
    op.add_column('media_assets',
        sa.Column('brand_name', sa.String(), nullable=True))
    op.add_column('media_assets',
        sa.Column('width', sa.Integer(), nullable=True))
    op.add_column('media_assets',
        sa.Column('height', sa.Integer(), nullable=True))
    op.create_index('idx_media_assets_brand_id', 'media_assets', ['brand_id'])

def downgrade() -> None:
    op.drop_index('idx_media_assets_brand_id', 'media_assets')
    op.drop_column('media_assets', 'brand_id')
    op.drop_column('media_assets', 'brand_name')
    op.drop_column('media_assets', 'width')
    op.drop_column('media_assets', 'height')