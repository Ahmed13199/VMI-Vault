"""add target ranges to metric_values

Revision ID: 0f1a2b3c4d5e
Revises: f1a2b3c4d5e6
Create Date: 2026-06-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0f1a2b3c4d5e'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('metric_values', schema=None) as batch_op:
        batch_op.add_column(sa.Column('target_type', sa.String(length=16), nullable=False, server_default='single'))
        batch_op.add_column(sa.Column('target_lower', sa.Numeric(precision=18, scale=4), nullable=True))
        batch_op.add_column(sa.Column('target_upper', sa.Numeric(precision=18, scale=4), nullable=True))

    with op.batch_alter_table('metric_values', schema=None) as batch_op:
        batch_op.alter_column('target_type', server_default=None)


def downgrade():
    with op.batch_alter_table('metric_values', schema=None) as batch_op:
        batch_op.drop_column('target_upper')
        batch_op.drop_column('target_lower')
        batch_op.drop_column('target_type')
