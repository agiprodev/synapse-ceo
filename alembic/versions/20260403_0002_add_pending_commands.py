"""add pending commands queue for reverse tunnel pull model

Revision ID: 20260403_0002
Revises: 20260403_0001
Create Date: 2026-04-03 00:00:02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260403_0002"
down_revision: Union[str, Sequence[str], None] = "20260403_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


command_status = sa.Enum("pending", "dispatched", "acked", "failed", name="command_status")


def upgrade() -> None:
    bind = op.get_bind()
    command_status.create(bind, checkfirst=True)

    op.create_table(
        "pending_commands",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(length=36), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("command", sa.String(length=128), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("signature", sa.String(length=255), nullable=False),
        sa.Column("incident_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", command_status, nullable=False, server_default="pending"),
        sa.Column("ack_message", sa.Text(), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_pending_commands_tenant_agent_status",
        "pending_commands",
        ["tenant_id", "agent_id", "status"],
    )
    op.create_index("ix_pending_commands_created_at", "pending_commands", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_commands_created_at", table_name="pending_commands")
    op.drop_index("ix_pending_commands_tenant_agent_status", table_name="pending_commands")
    op.drop_table("pending_commands")

    bind = op.get_bind()
    command_status.drop(bind, checkfirst=True)
