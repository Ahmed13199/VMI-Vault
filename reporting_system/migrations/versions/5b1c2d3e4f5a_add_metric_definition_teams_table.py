"""add metric_definition_teams table

Revision ID: 5b1c2d3e4f5a
Revises: 4a6b7c8d9e0f
Create Date: 2025-12-12 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b1c2d3e4f5a'
down_revision = '4a6b7c8d9e0f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'metric_definition_teams',
        sa.Column('metric_definition_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['metric_definition_id'], ['metric_definitions.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.PrimaryKeyConstraint('metric_definition_id', 'team_id')
    )

    # Backfill from legacy single-team metrics
    op.execute(
        """
        INSERT INTO metric_definition_teams (metric_definition_id, team_id)
        SELECT id, team_id
        FROM metric_definitions
        WHERE scope = 'team' AND team_id IS NOT NULL
        """
    )

    # Clear legacy column to avoid ambiguity going forward
    op.execute("UPDATE metric_definitions SET team_id = NULL WHERE scope = 'team'")


def downgrade():
    # Best-effort restore legacy single-team mapping (pick smallest team_id)
    op.execute(
        """
        UPDATE metric_definitions
        SET team_id = (
            SELECT MIN(mdt.team_id)
            FROM metric_definition_teams mdt
            WHERE mdt.metric_definition_id = metric_definitions.id
        )
        WHERE id IN (SELECT DISTINCT metric_definition_id FROM metric_definition_teams)
        """
    )

    op.drop_table('metric_definition_teams')
