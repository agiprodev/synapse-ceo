"""add sns message logs for idempotency and audit trail

Revision ID: 20260403_0003
Revises: 20260403_0002
Create Date: 2026-04-03 00:00:03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260403_0003"
down_revision: Union[str, Sequence[str], None] = "20260403_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sns_message_logs",
        sa.Column("message_id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("topic_arn", sa.String(length=255), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
    )
    op.create_index("ix_sns_message_logs_processed_at", "sns_message_logs", ["processed_at"])


def downgrade() -> None:
    op.drop_index("ix_sns_message_logs_processed_at", table_name="sns_message_logs")
    op.drop_table("sns_message_logs")
