"""convert hours unit to mins

Revision ID: 4a6b7c8d9e0f
Revises: 3f0c1a2b4d5e
Create Date: 2025-12-12 00:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '4a6b7c8d9e0f'
down_revision = '3f0c1a2b4d5e'
branch_labels = None
depends_on = None


def upgrade():
    # Convert existing 'hours' metrics to 'mins' and convert their stored values.
    # Update values first, then unit label.
    op.execute(
        """
        UPDATE metric_values
        SET value = value * 60
        WHERE metric_id IN (
            SELECT id FROM metric_definitions WHERE unit = 'hours'
        )
        """
    )

    op.execute("UPDATE metric_definitions SET unit = 'mins' WHERE unit = 'hours'")


def downgrade():
    # Convert 'mins' metrics back to 'hours' and convert their stored values.
    # Update values first, then unit label.
    op.execute(
        """
        UPDATE metric_values
        SET value = value / 60
        WHERE metric_id IN (
            SELECT id FROM metric_definitions WHERE unit = 'mins'
        )
        """
    )

    op.execute("UPDATE metric_definitions SET unit = 'hours' WHERE unit = 'mins'")
