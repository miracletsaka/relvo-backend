"""add ai chat tables

Revision ID: 5e601e80b70d
Revises: 9b2e4d6a1c58
Create Date: 2026-11-04 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5e601e80b70d'
down_revision: Union[str, Sequence[str], None] = '9b2e4d6a1c58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_chat_threads',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('brand_id', sa.String(length=100), nullable=True),
        sa.Column('tone_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tone_id'], ['tones.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_chat_threads_org_id'), 'ai_chat_threads', ['org_id'], unique=False)
    op.create_index(op.f('ix_ai_chat_threads_brand_id'), 'ai_chat_threads', ['brand_id'], unique=False)
    op.create_index(op.f('ix_ai_chat_threads_tone_id'), 'ai_chat_threads', ['tone_id'], unique=False)

    op.create_table(
        'ai_chat_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('thread_id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=40), nullable=False),
        sa.Column('meta_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('draft_id', sa.UUID(), nullable=True),
        sa.Column('canvas_state_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['ai_chat_threads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['organisations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['draft_id'], ['content_drafts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_chat_messages_thread_id'), 'ai_chat_messages', ['thread_id'], unique=False)
    op.create_index(op.f('ix_ai_chat_messages_org_id'), 'ai_chat_messages', ['org_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ai_chat_messages_org_id'), table_name='ai_chat_messages')
    op.drop_index(op.f('ix_ai_chat_messages_thread_id'), table_name='ai_chat_messages')
    op.drop_table('ai_chat_messages')
    op.drop_index(op.f('ix_ai_chat_threads_tone_id'), table_name='ai_chat_threads')
    op.drop_index(op.f('ix_ai_chat_threads_brand_id'), table_name='ai_chat_threads')
    op.drop_index(op.f('ix_ai_chat_threads_org_id'), table_name='ai_chat_threads')
    op.drop_table('ai_chat_threads')