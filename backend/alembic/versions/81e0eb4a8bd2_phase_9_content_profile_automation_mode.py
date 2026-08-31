"""phase 9: content profile automation mode

Revision ID: 81e0eb4a8bd2
Revises: 4a1731dd243b
Create Date: 2026-08-31 15:17:51.199689

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "81e0eb4a8bd2"
down_revision: str | Sequence[str] | None = "4a1731dd243b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills any pre-existing rows (Phase 1-8 profiles
    # created before this column existed) as MANUAL -- the safe default
    # per spec section 52, not autogenerate's usual bare NOT NULL.
    #
    # Postgres enum columns need the type created explicitly first --
    # inline sa.Enum(...) in add_column does not emit CREATE TYPE on its own.
    automation_mode = sa.Enum("MANUAL", "SEMI_AUTOMATIC", "AUTONOMOUS", name="automationmode")
    automation_mode.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "content_profiles",
        sa.Column(
            "automation_mode",
            automation_mode,
            nullable=False,
            server_default="MANUAL",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("content_profiles", "automation_mode")
    sa.Enum(name="automationmode").drop(op.get_bind(), checkfirst=True)
