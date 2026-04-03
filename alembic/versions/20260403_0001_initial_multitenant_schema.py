"""initial multi-tenant schema

Revision ID: 20260403_0001
Revises: 
Create Date: 2026-04-03 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260403_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


tenant_status = postgresql.ENUM(
    "active",
    "suspended",
    "trial",
    name="tenant_status",
    create_type=False,
    _create_events=False,
)
agent_status = postgresql.ENUM(
    "online",
    "offline",
    "degraded",
    name="agent_status",
    create_type=False,
    _create_events=False,
)
incident_status = postgresql.ENUM(
    "open",
    "auto_resolved",
    "escalated",
    "closed",
    name="incident_status",
    create_type=False,
    _create_events=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    tenant_status.create(bind, checkfirst=True)
    agent_status.create(bind, checkfirst=True)
    incident_status.create(bind, checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("external_ref", sa.String(length=255), nullable=True, unique=True),
        sa.Column("api_key_hash", sa.String(length=255), nullable=True),
        sa.Column("status", tenant_status, nullable=False, server_default="trial"),
        sa.Column("plan", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("environment", sa.String(length=64), nullable=False, server_default="prod"),
        sa.Column("status", agent_status, nullable=False, server_default="offline"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.UniqueConstraint("tenant_id", "hostname", name="uq_agents_tenant_hostname"),
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.String(length=36), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_rate", sa.Float(), nullable=True),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("status", incident_status, nullable=False, server_default="open"),
        sa.Column("action_taken", sa.String(length=128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("impact_dollars", sa.Float(), nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "marketplace_customers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("aws_customer_identifier", sa.String(length=255), nullable=False, unique=True),
        sa.Column("aws_product_code", sa.String(length=255), nullable=True),
        sa.Column("aws_account_id", sa.String(length=32), nullable=True),
        sa.Column("subscription_status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )

    op.create_index("ix_agents_tenant_id", "agents", ["tenant_id"])
    op.create_index("ix_agents_last_heartbeat", "agents", ["last_heartbeat_at"])
    op.create_index("ix_incidents_tenant_id", "incidents", ["tenant_id"])
    op.create_index("ix_incidents_agent_id", "incidents", ["agent_id"])
    op.create_index("ix_incidents_occurred_at", "incidents", ["occurred_at"])
    op.create_index("ix_marketplace_customers_tenant_id", "marketplace_customers", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_marketplace_customers_tenant_id", table_name="marketplace_customers")
    op.drop_index("ix_incidents_occurred_at", table_name="incidents")
    op.drop_index("ix_incidents_agent_id", table_name="incidents")
    op.drop_index("ix_incidents_tenant_id", table_name="incidents")
    op.drop_index("ix_agents_last_heartbeat", table_name="agents")
    op.drop_index("ix_agents_tenant_id", table_name="agents")

    op.drop_table("marketplace_customers")
    op.drop_table("incidents")
    op.drop_table("agents")
    op.drop_table("tenants")

    bind = op.get_bind()
    incident_status.drop(bind, checkfirst=True)
    agent_status.drop(bind, checkfirst=True)
    tenant_status.drop(bind, checkfirst=True)
