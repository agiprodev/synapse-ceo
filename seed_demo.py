"""Seed deterministic demo incidents for the pitch-deck dashboard.

Usage:
  python seed_demo.py
  python seed_demo.py --tenant-id demo-tenant --tenant-name "Acme Fintech" --reset
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from apps.api.db import SessionLocal
from apps.api.models import Agent, AgentStatus, Incident, IncidentStatus, Tenant, TenantStatus


@dataclass(frozen=True)
class DemoIncidentSpec:
    title: str
    summary: str
    status: IncidentStatus
    action_taken: str
    error_rate: float
    cpu_percent: float
    confidence: float
    impact_dollars: float
    escalated: bool
    occurred_hours_ago: int
    resolved_after_minutes: int | None


INCIDENT_SPECS: list[DemoIncidentSpec] = [
    DemoIncidentSpec("payment-service", "CPU spike hit checkout nodes", IncidentStatus.AUTO_RESOLVED, "rollback:v2.4.1", 19.6, 93.0, 0.96, 2450.0, False, 6, 7),
    DemoIncidentSpec("auth-api", "Memory leak in session worker", IncidentStatus.AUTO_RESOLVED, "restart:auth-worker", 14.2, 88.0, 0.93, 1800.0, False, 9, 5),
    DemoIncidentSpec("notification-bus", "Kafka lag surged over threshold", IncidentStatus.AUTO_RESOLVED, "scale_out:consumer-group", 11.1, 76.0, 0.89, 1120.0, False, 14, 12),
    DemoIncidentSpec("billing-core", "Unexpected 5xx burst on invoice API", IncidentStatus.ESCALATED, "escalate:oncall-billing", 17.8, 81.0, 0.62, 940.0, True, 21, None),
    DemoIncidentSpec("edge-gateway", "TLS handshake failures from one AZ", IncidentStatus.AUTO_RESOLVED, "shift_traffic:az-b", 8.3, 64.0, 0.91, 1300.0, False, 27, 15),
    DemoIncidentSpec("search-indexer", "Queue saturation at indexing cluster", IncidentStatus.AUTO_RESOLVED, "throttle:bulk-ingest", 7.6, 71.0, 0.87, 990.0, False, 33, 11),
    DemoIncidentSpec("payments-db", "Read replica replication delay", IncidentStatus.AUTO_RESOLVED, "promote_replica:db-r2", 9.4, 68.0, 0.9, 1650.0, False, 42, 10),
    DemoIncidentSpec("web-frontend", "Spike in JS runtime exceptions", IncidentStatus.ESCALATED, "escalate:frontend-oncall", 6.7, 58.0, 0.55, 520.0, True, 54, None),
    DemoIncidentSpec("recommendation-engine", "Hot shard over-utilization", IncidentStatus.AUTO_RESOLVED, "rebalance:shard-17", 10.5, 84.0, 0.9, 1420.0, False, 62, 9),
    DemoIncidentSpec("audit-pipeline", "Late event ingestion beyond SLA", IncidentStatus.AUTO_RESOLVED, "replay:partition-9", 5.9, 52.0, 0.88, 780.0, False, 77, 16),
    DemoIncidentSpec("auth-api", "Token introspection latency regression", IncidentStatus.AUTO_RESOLVED, "rollback:v5.2.0", 13.2, 79.0, 0.92, 1550.0, False, 96, 6),
    DemoIncidentSpec("payment-service", "Card authorization timeout anomaly", IncidentStatus.AUTO_RESOLVED, "restart:payment-worker", 12.8, 82.0, 0.9, 1700.0, False, 112, 8),
    DemoIncidentSpec("tenant-admin", "RBAC sync drift detected", IncidentStatus.ESCALATED, "escalate:security-team", 4.1, 47.0, 0.51, 430.0, True, 131, None),
    DemoIncidentSpec("stream-processor", "Backpressure in fraud stream", IncidentStatus.AUTO_RESOLVED, "scale_out:stream-workers", 8.7, 73.0, 0.9, 1330.0, False, 149, 13),
    DemoIncidentSpec("payments-db", "Connection pool exhaustion", IncidentStatus.AUTO_RESOLVED, "increase_pool:db-proxy", 9.1, 75.0, 0.9, 1470.0, False, 166, 12),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo data for dashboard showcase")
    parser.add_argument("--tenant-id", default="demo-tenant", help="Tenant ID to seed")
    parser.add_argument("--tenant-name", default="Demo Tenant", help="Tenant display name")
    parser.add_argument("--agent-hostname", default="demo-edge-agent-01", help="Agent hostname")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing incidents for this tenant before seeding",
    )
    return parser.parse_args()


def get_or_create_tenant(db, tenant_id: str, tenant_name: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant:
        tenant.name = tenant_name
        if tenant.status == TenantStatus.SUSPENDED:
            tenant.status = TenantStatus.ACTIVE
        return tenant

    tenant = Tenant(
        id=tenant_id,
        name=tenant_name,
        status=TenantStatus.ACTIVE,
        plan="marketplace-pro",
        external_ref=f"demo::{tenant_id}",
    )
    db.add(tenant)
    return tenant


def get_or_create_agent(db, tenant_id: str, hostname: str) -> Agent:
    agent = db.query(Agent).filter(Agent.tenant_id == tenant_id, Agent.hostname == hostname).first()
    if agent:
        agent.status = AgentStatus.ONLINE
        agent.environment = "prod"
        agent.last_heartbeat_at = datetime.now(timezone.utc)
        return agent

    agent = Agent(
        tenant_id=tenant_id,
        hostname=hostname,
        environment="prod",
        status=AgentStatus.ONLINE,
        last_heartbeat_at=datetime.now(timezone.utc),
        agent_metadata={"seeded": True, "source": "seed_demo.py"},
    )
    db.add(agent)
    return agent


def seed_incidents(db, tenant_id: str, agent_id: str) -> tuple[int, int, float]:
    now = datetime.now(timezone.utc)
    inserted = 0
    auto_resolved = 0
    total_impact = 0.0

    for spec in INCIDENT_SPECS:
        occurred_at = now - timedelta(hours=spec.occurred_hours_ago)
        resolved_at = None
        if spec.resolved_after_minutes is not None:
            resolved_at = occurred_at + timedelta(minutes=spec.resolved_after_minutes)

        incident = Incident(
            tenant_id=tenant_id,
            agent_id=agent_id,
            title=spec.title,
            summary=spec.summary,
            status=spec.status,
            action_taken=spec.action_taken,
            error_rate=spec.error_rate,
            cpu_percent=spec.cpu_percent,
            confidence=spec.confidence,
            impact_dollars=spec.impact_dollars,
            escalated=spec.escalated,
            raw_payload={"seeded": True, "service": spec.title},
            occurred_at=occurred_at,
            resolved_at=resolved_at,
        )
        db.add(incident)

        inserted += 1
        total_impact += spec.impact_dollars
        if spec.status == IncidentStatus.AUTO_RESOLVED:
            auto_resolved += 1

    return inserted, auto_resolved, total_impact


def main() -> None:
    args = parse_args()

    with SessionLocal() as db:
        tenant = get_or_create_tenant(db, args.tenant_id, args.tenant_name)
        db.flush()

        agent = get_or_create_agent(db, tenant.id, args.agent_hostname)
        db.flush()

        if args.reset:
            db.query(Incident).filter(Incident.tenant_id == tenant.id).delete(synchronize_session=False)

        inserted, auto_resolved, total_impact = seed_incidents(db, tenant.id, agent.id)
        db.commit()

    print("✅ Demo data seeded successfully")
    print(f"tenant_id={args.tenant_id}")
    print(f"incidents_inserted={inserted}")
    print(f"auto_resolved={auto_resolved}")
    print(f"protected_value=${total_impact:,.0f}")


if __name__ == "__main__":
    main()
