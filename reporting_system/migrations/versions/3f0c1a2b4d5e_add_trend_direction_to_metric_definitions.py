"""add trend_direction to metric_definitions

Revision ID: 3f0c1a2b4d5e
Revises: 2cb8d0cb303a
Create Date: 2025-12-12 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f0c1a2b4d5e'
down_revision = '2cb8d0cb303a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('metric_definitions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('trend_direction', sa.String(length=32), nullable=False, server_default='neutral'))


def downgrade():
    with op.batch_alter_table('metric_definitions', schema=None) as batch_op:
        batch_op.drop_column('trend_direction')
