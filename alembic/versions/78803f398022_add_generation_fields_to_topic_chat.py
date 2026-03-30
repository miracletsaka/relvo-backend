"""add generation fields to topic_chat

Revision ID: 78803f398022
Revises: a8c5365c966b
Create Date: 2026-03-30 13:59:05.894054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '78803f398022'
down_revision: Union[str, Sequence[str], None] = 'a8c5365c966b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('topic_chats', sa.Column('generation_status', sa.String(), nullable=True))
    op.add_column('topic_chats', sa.Column('generation_result', sa.JSON(), nullable=True))
    op.add_column('topic_chats', sa.Column('generation_error', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('topic_chats', 'generation_error')
    op.drop_column('topic_chats', 'generation_result')
    op.drop_column('topic_chats', 'generation_status')