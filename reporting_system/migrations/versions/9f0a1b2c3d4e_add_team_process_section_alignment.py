"""add team process section alignment

Revision ID: 9f0a1b2c3d4e
Revises: 8e4f1a2b3c4d
Create Date: 2025-12-16 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f0a1b2c3d4e'
down_revision = '8e4f1a2b3c4d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('team_process_sections', schema=None) as batch_op:
        batch_op.add_column(sa.Column('text_align', sa.String(length=16), nullable=False, server_default='left'))


def downgrade():
    with op.batch_alter_table('team_process_sections', schema=None) as batch_op:
        batch_op.drop_column('text_align')
