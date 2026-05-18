"""add rank and access permissions

Revision ID: f1a2b3c4d5e6
Revises: e9f1a2b3c4d5
Create Date: 2026-03-14 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e9f1a2b3c4d5'
branch_labels = None
depends_on = None


PAGE_NAMES = {
    'dashboard': 'Dashboard',
    'framework': 'Framework',
    'team_processes': 'Team Processes',
    'documents': 'Documents',
    'experience_team': 'Experience Team',
    'sales_team': 'Sales Team',
    'settings': 'Metric Settings',
    'reporting_input': 'Data Entry',
    'reporting_output': 'Results',
    'journal': 'Journal',
    'permissions': 'Access Control',
    'user_management': 'User Management',
    'team_management': 'Team Management',
}


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('first_name', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('last_name', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('rank', sa.String(length=32), nullable=False, server_default='agent'))
        batch_op.create_index('ix_users_rank', ['rank'], unique=False)

    op.execute("UPDATE users SET rank = 'admin' WHERE role = 'admin'")

    op.create_table(
        'access_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('page_key', sa.String(length=64), nullable=False),
        sa.Column('page_name', sa.String(length=128), nullable=False),
        sa.Column('rank', sa.String(length=32), nullable=False),
        sa.Column('can_view', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('can_edit', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('page_key', 'rank', name='uq_access_permissions_page_rank'),
    )

    with op.batch_alter_table('access_permissions', schema=None) as batch_op:
        batch_op.create_index('ix_access_permissions_page_key', ['page_key'], unique=False)
        batch_op.create_index('ix_access_permissions_rank', ['rank'], unique=False)

    for page_key, page_name in PAGE_NAMES.items():
        for rank in ('team_leader', 'senior', 'agent', 'admin'):
            can_view = page_key not in ('permissions', 'user_management', 'team_management') or rank == 'admin'
            can_edit = rank == 'admin' or page_key in (
                'team_processes',
                'documents',
                'experience_team',
                'sales_team',
                'settings',
                'reporting_input',
                'journal',
            )
            if page_key in ('permissions', 'user_management', 'team_management') and rank != 'admin':
                can_edit = False

            op.execute(
                sa.text(
                    """
                    INSERT INTO access_permissions (page_key, page_name, rank, can_view, can_edit)
                    VALUES (:page_key, :page_name, :rank, :can_view, :can_edit)
                    """
                ).bindparams(
                    page_key=page_key,
                    page_name=page_name,
                    rank=rank,
                    can_view=can_view,
                    can_edit=can_edit,
                )
            )

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('rank', server_default=None)


def downgrade():
    with op.batch_alter_table('access_permissions', schema=None) as batch_op:
        batch_op.drop_index('ix_access_permissions_rank')
        batch_op.drop_index('ix_access_permissions_page_key')
    op.drop_table('access_permissions')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_rank')
        batch_op.drop_column('rank')
        batch_op.drop_column('last_name')
        batch_op.drop_column('first_name')
