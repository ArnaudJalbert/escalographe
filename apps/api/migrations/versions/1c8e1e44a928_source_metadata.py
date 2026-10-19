"""Preserve source coverage and provenance metadata on ingestion runs.

Revision ID: 1c8e1e44a928
Revises: 7e9a13cc065a
"""

import sqlalchemy as sa
from alembic import op

revision = "1c8e1e44a928"
down_revision = "7e9a13cc065a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ingestion_runs", sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}")
    )


def downgrade():
    op.drop_column("ingestion_runs", "metadata_json")
