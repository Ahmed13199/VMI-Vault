"""add documents tables

Revision ID: b2c3d4e5f607
Revises: a1b2c3d4e5f6
Create Date: 2025-12-17 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f607'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'document_folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['document_folders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('document_folders', schema=None) as batch_op:
        batch_op.create_index('ix_document_folders_parent_id', ['parent_id'], unique=False)
        batch_op.create_index('ix_document_folders_created_by_user_id', ['created_by_user_id'], unique=False)

    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('folder_id', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('original_filename', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=200), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('storage_key', sa.String(length=700), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['folder_id'], ['document_folders.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_key')
    )
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.create_index('ix_documents_folder_id', ['folder_id'], unique=False)
        batch_op.create_index('ix_documents_created_by_user_id', ['created_by_user_id'], unique=False)
        batch_op.create_index('ix_documents_storage_key', ['storage_key'], unique=False)


def downgrade():
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index('ix_documents_storage_key')
        batch_op.drop_index('ix_documents_created_by_user_id')
        batch_op.drop_index('ix_documents_folder_id')

    op.drop_table('documents')

    with op.batch_alter_table('document_folders', schema=None) as batch_op:
        batch_op.drop_index('ix_document_folders_created_by_user_id')
        batch_op.drop_index('ix_document_folders_parent_id')

    op.drop_table('document_folders')
