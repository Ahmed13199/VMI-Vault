"""add sales team guideline tables

Revision ID: e9f1a2b3c4d5
Revises: d8e9f0a1b2c3
Create Date: 2026-03-10 22:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e9f1a2b3c4d5'
down_revision = 'd8e9f0a1b2c3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sales_guideline_partitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sales_guideline_partitions', schema=None) as batch_op:
        batch_op.create_index('ix_sales_guideline_partitions_created_by_user_id', ['created_by_user_id'], unique=False)

    op.create_table(
        'sales_guideline_sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('partition_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['partition_id'], ['sales_guideline_partitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sales_guideline_sections', schema=None) as batch_op:
        batch_op.create_index('ix_sales_guideline_sections_created_by_user_id', ['created_by_user_id'], unique=False)
        batch_op.create_index('ix_sales_guideline_sections_partition_id', ['partition_id'], unique=False)

    op.create_table(
        'sales_guideline_subsections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['section_id'], ['sales_guideline_sections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sales_guideline_subsections', schema=None) as batch_op:
        batch_op.create_index('ix_sales_guideline_subsections_created_by_user_id', ['created_by_user_id'], unique=False)
        batch_op.create_index('ix_sales_guideline_subsections_section_id', ['section_id'], unique=False)

    op.create_table(
        'sales_guideline_resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subsection_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('resource_type', sa.String(length=16), nullable=False, server_default='link'),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('storage_key', sa.String(length=700), nullable=True),
        sa.Column('original_filename', sa.String(length=500), nullable=True),
        sa.Column('content_type', sa.String(length=200), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("resource_type IN ('file', 'link')", name='ck_sales_guideline_resource_type'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subsection_id'], ['sales_guideline_subsections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_key')
    )
    with op.batch_alter_table('sales_guideline_resources', schema=None) as batch_op:
        batch_op.create_index('ix_sales_guideline_resources_created_by_user_id', ['created_by_user_id'], unique=False)
        batch_op.create_index('ix_sales_guideline_resources_storage_key', ['storage_key'], unique=False)
        batch_op.create_index('ix_sales_guideline_resources_subsection_id', ['subsection_id'], unique=False)


def downgrade():
    with op.batch_alter_table('sales_guideline_resources', schema=None) as batch_op:
        batch_op.drop_index('ix_sales_guideline_resources_subsection_id')
        batch_op.drop_index('ix_sales_guideline_resources_storage_key')
        batch_op.drop_index('ix_sales_guideline_resources_created_by_user_id')
    op.drop_table('sales_guideline_resources')

    with op.batch_alter_table('sales_guideline_subsections', schema=None) as batch_op:
        batch_op.drop_index('ix_sales_guideline_subsections_section_id')
        batch_op.drop_index('ix_sales_guideline_subsections_created_by_user_id')
    op.drop_table('sales_guideline_subsections')

    with op.batch_alter_table('sales_guideline_sections', schema=None) as batch_op:
        batch_op.drop_index('ix_sales_guideline_sections_partition_id')
        batch_op.drop_index('ix_sales_guideline_sections_created_by_user_id')
    op.drop_table('sales_guideline_sections')

    with op.batch_alter_table('sales_guideline_partitions', schema=None) as batch_op:
        batch_op.drop_index('ix_sales_guideline_partitions_created_by_user_id')
    op.drop_table('sales_guideline_partitions')
