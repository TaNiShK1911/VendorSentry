"""Add website_domain to vendors and external_id to breach_events

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-21 15:30:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add website_domain to vendors
    op.add_column("vendors", sa.Column("website_domain", sa.String(255), nullable=True))

    # Add external_id to breach_events for HIBP dedup
    op.add_column("breach_events", sa.Column("external_id", sa.String(255), nullable=True))
    op.create_index("ix_breach_events_external_id", "breach_events", ["external_id"])

    # Backfill website_domain from contact email where possible
    # SQLite doesn't support UPDATE ... FROM with JSON extraction the same way,
    # so we do this via a Python data migration
    conn = op.get_bind()

    # Check if this is SQLite (which stores JSON as text)
    is_sqlite = conn.dialect.name == "sqlite"

    if is_sqlite:
        import json

        rows = conn.execute(
            sa.text("SELECT id, contact FROM vendors WHERE contact IS NOT NULL")
        ).fetchall()

        for row in rows:
            vendor_id = row[0]
            contact_raw = row[1]
            if contact_raw:
                try:
                    contact = json.loads(contact_raw) if isinstance(contact_raw, str) else contact_raw
                    email = contact.get("email", "") if isinstance(contact, dict) else ""
                    if email and "@" in email:
                        domain = email.split("@")[1].lower().strip()
                        conn.execute(
                            sa.text("UPDATE vendors SET website_domain = :domain WHERE id = :id"),
                            {"domain": domain, "id": vendor_id},
                        )
                except (json.JSONDecodeError, AttributeError, IndexError):
                    pass  # Skip vendors with malformed contact data
    else:
        # PostgreSQL: use JSON extraction
        conn.execute(
            sa.text("""
                UPDATE vendors
                SET website_domain = LOWER(SPLIT_PART(contact->>'email', '@', 2))
                WHERE contact->>'email' IS NOT NULL
                  AND contact->>'email' LIKE '%@%'
                  AND website_domain IS NULL
            """)
        )


def downgrade() -> None:
    op.drop_index("ix_breach_events_external_id", table_name="breach_events")
    op.drop_column("breach_events", "external_id")
    op.drop_column("vendors", "website_domain")
