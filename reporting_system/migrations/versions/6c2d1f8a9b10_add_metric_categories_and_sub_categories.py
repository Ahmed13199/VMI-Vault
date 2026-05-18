"""add metric categories and sub categories

Revision ID: 6c2d1f8a9b10
Revises: 5b1c2d3e4f5a
Create Date: 2025-12-14 18:08:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6c2d1f8a9b10'
down_revision = '5b1c2d3e4f5a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'metric_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    with op.batch_alter_table('metric_categories', schema=None) as batch_op:
        batch_op.create_index('ix_metric_categories_name', ['name'], unique=True)

    op.create_table(
        'metric_sub_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['metric_categories.id'], name='fk_metric_sub_categories_category_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id', 'name', name='uq_metric_sub_category_category_name')
    )
    with op.batch_alter_table('metric_sub_categories', schema=None) as batch_op:
        batch_op.create_index('ix_metric_sub_categories_category_id', ['category_id'], unique=False)

    with op.batch_alter_table('metric_definitions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('sub_category_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_metric_definitions_category_id', ['category_id'], unique=False)
        batch_op.create_index('ix_metric_definitions_sub_category_id', ['sub_category_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_metric_definitions_category_id_metric_categories',
            'metric_categories',
            ['category_id'],
            ['id']
        )
        batch_op.create_foreign_key(
            'fk_metric_definitions_sub_category_id_metric_sub_categories',
            'metric_sub_categories',
            ['sub_category_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('metric_definitions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_metric_definitions_sub_category_id_metric_sub_categories', type_='foreignkey')
        batch_op.drop_constraint('fk_metric_definitions_category_id_metric_categories', type_='foreignkey')
        batch_op.drop_index('ix_metric_definitions_sub_category_id')
        batch_op.drop_index('ix_metric_definitions_category_id')
        batch_op.drop_column('sub_category_id')
        batch_op.drop_column('category_id')

    with op.batch_alter_table('metric_sub_categories', schema=None) as batch_op:
        batch_op.drop_index('ix_metric_sub_categories_category_id')

    op.drop_table('metric_sub_categories')

    with op.batch_alter_table('metric_categories', schema=None) as batch_op:
        batch_op.drop_index('ix_metric_categories_name')

    op.drop_table('metric_categories')
