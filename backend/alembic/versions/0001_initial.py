"""create initial business schema

Revision ID: 0001_initial
Revises:
"""

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Canonical table definitions live in app.models. This migration uses
    # metadata creation for the SQLite PoC and remains explicit in the chain.
    from sqlalchemy import create_engine

    from app.config import get_settings
    from app.models import Base

    engine = create_engine(f"sqlite:///{get_settings().business_db_path}")
    Base.metadata.create_all(engine)


def downgrade() -> None:
    from sqlalchemy import create_engine

    from app.config import get_settings
    from app.models import Base

    engine = create_engine(f"sqlite:///{get_settings().business_db_path}")
    Base.metadata.drop_all(engine)
