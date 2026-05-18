"""add team process section title html

Revision ID: a1b2c3d4e5f6
Revises: 9f0a1b2c3d4e
Create Date: 2025-12-16 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9f0a1b2c3d4e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('team_process_sections', schema=None) as batch_op:
        batch_op.add_column(sa.Column('title_html', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('team_process_sections', schema=None) as batch_op:
        batch_op.drop_column('title_html')
