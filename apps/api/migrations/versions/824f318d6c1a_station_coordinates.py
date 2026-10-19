"""Add station centroid and provenance fields without altering device coordinates.

Revision ID: 824f318d6c1a
Revises: 1c8e1e44a928
"""

import sqlalchemy as sa
from alembic import op

revision = "824f318d6c1a"
down_revision = "1c8e1e44a928"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("stations") as batch:
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("coordinate_source", sa.String(), nullable=True))
        batch.add_column(sa.Column("coordinate_version", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("stations") as batch:
        batch.drop_column("coordinate_version")
        batch.drop_column("coordinate_source")
        batch.drop_column("longitude")
        batch.drop_column("latitude")
