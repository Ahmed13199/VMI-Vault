"""add journal tables

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2025-12-22 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8e9f0a1b2c3'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'journal_tables',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'journal_table_rows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['table_id'], ['journal_tables.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('table_id', 'position', name='uq_journal_rows_table_position')
    )
    with op.batch_alter_table('journal_table_rows', schema=None) as batch_op:
        batch_op.create_index('ix_journal_rows_table_id', ['table_id'], unique=False)

    op.create_table(
        'journal_table_columns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['table_id'], ['journal_tables.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('table_id', 'position', name='uq_journal_cols_table_position')
    )
    with op.batch_alter_table('journal_table_columns', schema=None) as batch_op:
        batch_op.create_index('ix_journal_cols_table_id', ['table_id'], unique=False)

    op.create_table(
        'journal_table_cells',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=False),
        sa.Column('row_id', sa.Integer(), nullable=False),
        sa.Column('column_id', sa.Integer(), nullable=False),
        sa.Column('value_text', sa.Text(), nullable=True),
        sa.Column('value_number', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('(value_text IS NULL) OR (value_number IS NULL)', name='ck_journal_cell_one_type'),
        sa.ForeignKeyConstraint(['column_id'], ['journal_table_columns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['row_id'], ['journal_table_rows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['table_id'], ['journal_tables.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('table_id', 'row_id', 'column_id', name='uq_journal_cells_unique')
    )
    with op.batch_alter_table('journal_table_cells', schema=None) as batch_op:
        batch_op.create_index('ix_journal_cells_table_id', ['table_id'], unique=False)


def downgrade():
    with op.batch_alter_table('journal_table_cells', schema=None) as batch_op:
        batch_op.drop_index('ix_journal_cells_table_id')

    op.drop_table('journal_table_cells')

    with op.batch_alter_table('journal_table_columns', schema=None) as batch_op:
        batch_op.drop_index('ix_journal_cols_table_id')

    op.drop_table('journal_table_columns')

    with op.batch_alter_table('journal_table_rows', schema=None) as batch_op:
        batch_op.drop_index('ix_journal_rows_table_id')

    op.drop_table('journal_table_rows')

    op.drop_table('journal_tables')
