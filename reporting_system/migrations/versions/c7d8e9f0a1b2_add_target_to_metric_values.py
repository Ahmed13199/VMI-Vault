"""add target to metric_values

Revision ID: c7d8e9f0a1b2
Revises: b2c3d4e5f607
Create Date: 2025-12-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7d8e9f0a1b2'
down_revision = 'b2c3d4e5f607'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('metric_values', schema=None) as batch_op:
        batch_op.add_column(sa.Column('target', sa.Numeric(precision=18, scale=4), nullable=True))


def downgrade():
    with op.batch_alter_table('metric_values', schema=None) as batch_op:
        batch_op.drop_column('target')
