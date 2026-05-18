"""add team processes tables

Revision ID: 7d1e2f3a4b5c
Revises: 6c2d1f8a9b10
Create Date: 2025-12-16 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d1e2f3a4b5c'
down_revision = '6c2d1f8a9b10'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'team_processes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'slug', name='uq_team_process_team_slug')
    )
    with op.batch_alter_table('team_processes', schema=None) as batch_op:
        batch_op.create_index('ix_team_processes_team_id', ['team_id'], unique=False)

    op.create_table(
        'team_process_sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('process_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('section_type', sa.String(length=32), nullable=False, server_default='paragraph'),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['process_id'], ['team_processes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('team_process_sections', schema=None) as batch_op:
        batch_op.create_index('ix_team_process_sections_process_id', ['process_id'], unique=False)


def downgrade():
    with op.batch_alter_table('team_process_sections', schema=None) as batch_op:
        batch_op.drop_index('ix_team_process_sections_process_id')

    op.drop_table('team_process_sections')

    with op.batch_alter_table('team_processes', schema=None) as batch_op:
        batch_op.drop_index('ix_team_processes_team_id')

    op.drop_table('team_processes')
