import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class AgentStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    AUTO_RESOLVED = "auto_resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class CommandStatus(str, enum.Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    ACKED = "acked"
    FAILED = "failed"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(255), unique=True)
    api_key_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenant_status", values_callable=_enum_values),
        default=TenantStatus.TRIAL,
        nullable=False,
    )
    plan: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    agents: Mapped[list["Agent"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    pending_commands: Mapped[list["PendingCommand"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    marketplace_customer: Mapped["MarketplaceCustomer | None"] = relationship(
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("tenant_id", "hostname", name="uq_agents_tenant_hostname"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    environment: Mapped[str] = mapped_column(String(64), default="prod", nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status", values_callable=_enum_values),
        default=AgentStatus.OFFLINE,
        nullable=False,
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    agent_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)

    tenant: Mapped[Tenant] = relationship(back_populates="agents")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="agent")
    pending_commands: Mapped[list["PendingCommand"]] = relationship(back_populates="agent")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"))

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    error_rate: Mapped[float | None] = mapped_column(Float)
    cpu_percent: Mapped[float | None] = mapped_column(Float)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status", values_callable=_enum_values),
        default=IncidentStatus.OPEN,
        nullable=False,
    )
    action_taken: Mapped[str | None] = mapped_column(String(128))
    confidence: Mapped[float | None] = mapped_column(Float)
    impact_dollars: Mapped[float | None] = mapped_column(Float)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant: Mapped[Tenant] = relationship(back_populates="incidents")
    agent: Mapped[Agent | None] = relationship(back_populates="incidents")


class MarketplaceCustomer(Base):
    __tablename__ = "marketplace_customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    aws_customer_identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    aws_product_code: Mapped[str | None] = mapped_column(String(255))
    aws_account_id: Mapped[str | None] = mapped_column(String(32))
    subscription_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict | None] = mapped_column(JSON)

    tenant: Mapped[Tenant] = relationship(back_populates="marketplace_customer")


class PendingCommand(Base):
    __tablename__ = "pending_commands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    command: Mapped[str] = mapped_column(String(128), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    incident_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[CommandStatus] = mapped_column(
        Enum(CommandStatus, name="command_status", values_callable=_enum_values),
        default=CommandStatus.PENDING,
        nullable=False,
    )
    ack_message: Mapped[str | None] = mapped_column(Text)
    result_payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant: Mapped[Tenant] = relationship(back_populates="pending_commands")
    agent: Mapped[Agent] = relationship(back_populates="pending_commands")


class SnsMessageLog(Base):
    __tablename__ = "sns_message_logs"

    message_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    topic_arn: Mapped[str] = mapped_column(String(255), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)


Index("ix_agents_tenant_id", Agent.tenant_id)
Index("ix_agents_last_heartbeat", Agent.last_heartbeat_at)
Index("ix_incidents_tenant_id", Incident.tenant_id)
Index("ix_incidents_agent_id", Incident.agent_id)
Index("ix_incidents_occurred_at", Incident.occurred_at)
Index("ix_marketplace_customers_tenant_id", MarketplaceCustomer.tenant_id)
Index("ix_pending_commands_tenant_agent_status", PendingCommand.tenant_id, PendingCommand.agent_id, PendingCommand.status)
Index("ix_pending_commands_created_at", PendingCommand.created_at)
Index("ix_sns_message_logs_processed_at", SnsMessageLog.processed_at)
