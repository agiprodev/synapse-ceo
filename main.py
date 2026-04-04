import asyncio
import json
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
import psutil
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import Depends

# --- Imports الخاصين بالوحش ---
from apps.api.learning.brain import DecisionEngine
from apps.api.security.signer import sign_action
from apps.api.actions.pending import ApprovalManager
from apps.api.learning.memory_store import MemoryStore
from apps.api.db import get_db
from agent.synapse_pulse import SynapsePulse, load_config
from apps.api.models import (
    Agent,
    AgentStatus,
    CommandStatus,
    Incident,
    IncidentStatus,
    PendingCommand,
    Tenant,
    TenantStatus,
)

app = FastAPI(title="Synapse Beast Central Node")
memory_store = MemoryStore()


@app.get("/", include_in_schema=False)
async def root_dashboard_page():
    return FileResponse("dashboard.html")


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page():
    return FileResponse("dashboard.html")


@app.get("/stream", include_in_schema=False)
async def stream_metrics():
    async def event_generator():
        monitor = SynapsePulse(load_config())
        psutil.cpu_percent()

        while True:
            await asyncio.sleep(1)
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            yield f"data: {json.dumps({'type': 'metrics', 'cpu': cpu, 'mem': mem})}\n\n"

            alert = monitor.analyze(cpu_now=cpu, mem_percent=mem)
            if alert:
                alert_data = {
                    "type": "alert",
                    "severity": alert.severity,
                    "reasoning": alert.reasoning,
                    "action": alert.action,
                    "cmd": alert.remediation_cmd or "Scaling triggered automatically",
                }
                yield f"data: {json.dumps(alert_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

class IncidentPayload(BaseModel):
    customer_id: str
    agent_id: str
    cpu_percent: float
    mem_percent: float
    disk_usage: float
    recent_logs: str
    metadata: dict


class AgentRegisterPayload(BaseModel):
    tenant_id: str
    hostname: str
    environment: str = "prod"
    metadata: dict | None = None


class AgentHeartbeatPayload(BaseModel):
    tenant_id: str
    agent_id: str
    metrics: dict | None = None

class CommandAckPayload(BaseModel):
    tenant_id: str
    agent_id: str
    status: str
    message: str | None = None
    result_payload: dict | None = None


class DashboardIncidentItem(BaseModel):
    id: str
    title: str
    status: str
    cpu_percent: float | None = None
    error_rate: float | None = None
    action_taken: str | None = None
    impact_dollars: float | None = None
    occurred_at: datetime
    resolved_at: datetime | None = None


class DashboardIncidentsResponse(BaseModel):
    tenant_id: str
    total: int
    incidents: list[DashboardIncidentItem]


class DashboardRoiResponse(BaseModel):
    tenant_id: str
    incidents_count: int
    auto_resolved_count: int
    escalated_count: int
    total_impact_dollars: float
    period_days: int


async def queue_action_for_agent(
    db: Session,
    *,
    tenant_id: str,
    agent_id: str,
    action_data: dict,
    incident_text: str,
    confidence: float,
):
    """Queue action for edge agent pull model (reverse tunnel safe)."""

    signature = sign_action(action_data)
    queued = PendingCommand(
        tenant_id=tenant_id,
        agent_id=agent_id,
        command=action_data["command"],
        target=action_data["target"],
        signature=signature,
        incident_text=incident_text,
        confidence=confidence,
        status=CommandStatus.PENDING,
    )
    db.add(queued)
    db.commit()
    db.refresh(queued)

    return {
        "status": "QUEUED_FOR_AGENT",
        "command_id": queued.id,
        "queued_at": queued.created_at,
    }

@app.post("/v1/decide")
async def decide_incident(payload: IncidentPayload, x_api_key: str = Header(None), db: Session = Depends(get_db)):
    if x_api_key != "test_key":
        raise HTTPException(status_code=403, detail="Invalid API Key")

    # 🧠 المخ بيفكر ويسترجع الذكريات
    result = DecisionEngine.process_incident(payload.dict())
    details = result["details"]

    # 🚀 مسار الطيران الآلي (Auto-Pilot)
    if result["status"] == "EXECUTING_NOW":
        action_data = {
            "command": details["action"],
            "target": details["target"]
        }
        
        try:
            exec_result = await queue_action_for_agent(
                db=db,
                tenant_id=payload.customer_id,
                agent_id=payload.agent_id,
                action_data=action_data,
                incident_text=details["incident_text"],
                confidence=details["confidence"],
            )
            return {
                "status": "AUTO_QUEUED",
                "reason": details["reason"],
                "execution_details": exec_result
            }
        except Exception as e:
            return {"status": "AUTO_EXEC_FAILED", "error": str(e)}

    # ⏳ مسار الموافقة اليدوية (Manual Approval)
    return {
        "status": result["status"],
        "action_id": result.get("action_id"),
        "message": details["reason"],
        "history_count": details.get("history_count", 0)
    }

@app.post("/v1/approve/{action_id}")
async def approve_action(action_id: str, db: Session = Depends(get_db)):
    action_data = ApprovalManager.approve(action_id)
    if not action_data:
        raise HTTPException(status_code=404, detail="Action ID not found or already executed")
    
    # الأكشن داتا متخزن فيها الـ incident_text والـ confidence من الـ Brain
    payload_to_exec = {
        "command": action_data["command"],
        "target": action_data["target"]
    }
    customer_id = action_data.get("customer_id")
    agent_id = action_data.get("agent_id")
    if not customer_id or not agent_id:
        raise HTTPException(status_code=400, detail="Pending action missing customer_id or agent_id")
    
    try:
        exec_result = await queue_action_for_agent(
            db=db,
            tenant_id=customer_id,
            agent_id=agent_id,
            action_data=payload_to_exec,
            incident_text=action_data.get("incident_text", "Manual Approval Incident"),
            confidence=action_data.get("confidence", 1.0),
        )
        return exec_result
    except Exception as e:
        return {"status": "EXECUTION_FAILED", "error": str(e)}


@app.post("/v1/agents/register")
async def register_agent(payload: AgentRegisterPayload, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == payload.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if tenant.status == TenantStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="Tenant is suspended")

    agent = (
        db.query(Agent)
        .filter(Agent.tenant_id == payload.tenant_id, Agent.hostname == payload.hostname)
        .first()
    )

    if not agent:
        agent = Agent(
            tenant_id=payload.tenant_id,
            hostname=payload.hostname,
            environment=payload.environment,
            status=AgentStatus.ONLINE,
            last_heartbeat_at=datetime.now(timezone.utc),
            agent_metadata=payload.metadata,
        )
        db.add(agent)
    else:
        agent.environment = payload.environment
        agent.status = AgentStatus.ONLINE
        agent.last_heartbeat_at = datetime.now(timezone.utc)
        agent.agent_metadata = payload.metadata or agent.agent_metadata

    db.commit()
    db.refresh(agent)

    return {
        "status": "registered",
        "agent_id": agent.id,
        "tenant_id": agent.tenant_id,
        "hostname": agent.hostname,
        "last_heartbeat_at": agent.last_heartbeat_at,
    }


@app.post("/v1/agents/heartbeat")
async def agent_heartbeat(payload: AgentHeartbeatPayload, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == payload.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if tenant.status == TenantStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="Tenant is suspended")

    agent = (
        db.query(Agent)
        .filter(Agent.id == payload.agent_id, Agent.tenant_id == payload.tenant_id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = AgentStatus.ONLINE
    agent.last_heartbeat_at = datetime.now(timezone.utc)
    if payload.metrics:
        updated_metadata = dict(agent.agent_metadata or {})
        updated_metadata["last_metrics"] = payload.metrics
        agent.agent_metadata = updated_metadata

    db.commit()

    return {
        "status": "alive",
        "agent_id": agent.id,
        "tenant_id": agent.tenant_id,
        "last_heartbeat_at": agent.last_heartbeat_at,
    }


@app.get("/v1/agents/commands/next")
async def get_next_command(
    tenant_id: str = Query(...),
    agent_id: str = Query(...),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.status == TenantStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="Tenant is suspended")

    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.tenant_id == tenant_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    command = (
        db.query(PendingCommand)
        .filter(
            PendingCommand.tenant_id == tenant_id,
            PendingCommand.agent_id == agent_id,
            PendingCommand.status == CommandStatus.PENDING,
        )
        .order_by(PendingCommand.created_at.asc())
        .first()
    )
    if not command:
        return {"status": "NO_PENDING_COMMANDS"}

    command.status = CommandStatus.DISPATCHED
    command.dispatched_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(command)

    return {
        "status": "COMMAND_DISPATCHED",
        "command_id": command.id,
        "payload": {
            "command": command.command,
            "target": command.target,
        },
        "signature": command.signature,
        "incident_text": command.incident_text,
        "confidence": command.confidence,
    }


@app.post("/v1/agents/commands/{command_id}/ack")
async def ack_command(command_id: str, payload: CommandAckPayload, db: Session = Depends(get_db)):
    command = (
        db.query(PendingCommand)
        .filter(
            PendingCommand.id == command_id,
            PendingCommand.tenant_id == payload.tenant_id,
            PendingCommand.agent_id == payload.agent_id,
        )
        .first()
    )
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    normalized = payload.status.strip().lower()
    if normalized in {"ok", "success", "acked"}:
        command.status = CommandStatus.ACKED
    elif normalized in {"failed", "error"}:
        command.status = CommandStatus.FAILED
    else:
        raise HTTPException(status_code=400, detail="Invalid command status")

    command.ack_message = payload.message
    command.result_payload = payload.result_payload
    command.acked_at = datetime.now(timezone.utc)
    db.commit()

    if command.status == CommandStatus.ACKED:
        memory_store.upsert_success_memory(
            action_id=command.id,
            incident_text=command.incident_text or "Agent executed queued command",
            action_taken=command.command,
            target=command.target,
            confidence=command.confidence or 1.0,
            impact_dollars=0.0,
            cpu_before=0.0,
            cpu_after=0.0,
        )

    return {"status": command.status.value, "command_id": command.id}


@app.get("/v1/dashboard/incidents", response_model=DashboardIncidentsResponse)
async def dashboard_incidents(
    tenant_id: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    query = db.query(Incident).filter(Incident.tenant_id == tenant_id)
    if status:
        normalized = status.strip().lower()
        allowed = {item.value for item in IncidentStatus}
        if normalized not in allowed:
            raise HTTPException(status_code=400, detail="Invalid incident status filter")
        query = query.filter(Incident.status == IncidentStatus(normalized))

    rows = query.order_by(Incident.occurred_at.desc()).limit(limit).all()

    return DashboardIncidentsResponse(
        tenant_id=tenant_id,
        total=len(rows),
        incidents=[
            DashboardIncidentItem(
                id=row.id,
                title=row.title,
                status=row.status.value,
                cpu_percent=row.cpu_percent,
                error_rate=row.error_rate,
                action_taken=row.action_taken,
                impact_dollars=row.impact_dollars,
                occurred_at=row.occurred_at,
                resolved_at=row.resolved_at,
            )
            for row in rows
        ],
    )


@app.get("/v1/dashboard/roi", response_model=DashboardRoiResponse)
async def dashboard_roi(
    tenant_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    window_start = datetime.now(timezone.utc) - timedelta(days=days)
    base_query = db.query(Incident).filter(
        Incident.tenant_id == tenant_id,
        Incident.occurred_at >= window_start,
    )

    incidents_count = base_query.count()
    auto_resolved_count = base_query.filter(Incident.status == IncidentStatus.AUTO_RESOLVED).count()
    escalated_count = base_query.filter(Incident.status == IncidentStatus.ESCALATED).count()
    total_impact_dollars = (
        db.query(func.coalesce(func.sum(Incident.impact_dollars), 0.0))
        .filter(
            Incident.tenant_id == tenant_id,
            Incident.occurred_at >= window_start,
        )
        .scalar()
    )

    return DashboardRoiResponse(
        tenant_id=tenant_id,
        incidents_count=incidents_count,
        auto_resolved_count=auto_resolved_count,
        escalated_count=escalated_count,
        total_impact_dollars=float(total_impact_dollars or 0.0),
        period_days=days,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5555)
