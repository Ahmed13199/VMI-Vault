"""add team process creators

Revision ID: 8e4f1a2b3c4d
Revises: 7d1e2f3a4b5c
Create Date: 2025-12-16 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8e4f1a2b3c4d'
down_revision = '7d1e2f3a4b5c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('team_processes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by_user_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_team_processes_created_by_user_id', ['created_by_user_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_team_processes_created_by_user_id_users',
            'users',
            ['created_by_user_id'],
            ['id']
        )

    with op.batch_alter_table('team_process_sections', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by_user_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_team_process_sections_created_by_user_id', ['created_by_user_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_team_process_sections_created_by_user_id_users',
            'users',
            ['created_by_user_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('team_process_sections', schema=None) as batch_op:
        batch_op.drop_constraint('fk_team_process_sections_created_by_user_id_users', type_='foreignkey')
        batch_op.drop_index('ix_team_process_sections_created_by_user_id')
        batch_op.drop_column('created_by_user_id')

    with op.batch_alter_table('team_processes', schema=None) as batch_op:
        batch_op.drop_constraint('fk_team_processes_created_by_user_id_users', type_='foreignkey')
        batch_op.drop_index('ix_team_processes_created_by_user_id')
        batch_op.drop_column('created_by_user_id')
