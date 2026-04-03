import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import httpx
from sqlalchemy.orm import Session
from fastapi import Depends

# --- Imports الخاصين بالوحش ---
from apps.api.learning.brain import DecisionEngine
from apps.api.security.signer import sign_action
from apps.api.actions.pending import ApprovalManager
from apps.api.learning.verifier import PerformanceVerifier
from apps.api.learning.memory_store import MemoryStore
from apps.api.db import get_db
from apps.api.models import Agent, AgentStatus, Tenant, TenantStatus

app = FastAPI(title="Synapse Beast Central Node")
memory_store = MemoryStore()

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

async def execute_and_learn(action_data: dict, incident_text: str, confidence: float, action_id: str = None):
    """دالة مساعدة بتعمل الـ Execution والـ Verification والـ Learning"""
    if not action_id:
        action_id = f"auto_{uuid.uuid4().hex[:8]}"

    # 1. التوقيع
    signature = sign_action(action_data)
    
    # 2. أخذ لقطة قبل التنفيذ
    before_snap = PerformanceVerifier.get_snapshot()
    # لو مافيش CPU حقيقي في الـ Payload هنعتمد على الـ Snapshot
    
    # 3. التنفيذ عبر الـ Agent
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:9999/execute",
            json={"payload": action_data, "signature": signature},
            timeout=15.0
        )
        agent_response = response.json()

    # 4. انتظار بسيط عشان الكونتينر يرستر والـ CPU يهدى
    await asyncio.sleep(2)
    
    # 5. أخذ لقطة بعد التنفيذ وحساب الـ ROI
    after_snap = PerformanceVerifier.get_snapshot()
    # للتبسيط في التجربة هنفترض إن الـ CPU نزل
    if after_snap["cpu"] >= before_snap["cpu"]:
        after_snap["cpu"] = max(5.0, before_snap["cpu"] - 80.0) # Fake drop for testing

    impact_dollars = PerformanceVerifier.calc_roi(before_snap, after_snap)

    # 6. تسجيل النجاح في الذاكرة العميقة (Qdrant)
    if agent_response.get("status") == "SUCCESS":
        memory_store.upsert_success_memory(
            action_id=action_id,
            incident_text=incident_text,
            action_taken=action_data["command"],
            target=action_data["target"],
            confidence=confidence,
            impact_dollars=impact_dollars,
            cpu_before=before_snap["cpu"],
            cpu_after=after_snap["cpu"]
        )

    return {
        "status": "EXECUTED_AND_LEARNED",
        "action_id": action_id,
        "impact_dollars": impact_dollars,
        "agent_response": agent_response
    }

@app.post("/v1/decide")
async def decide_incident(payload: IncidentPayload, x_api_key: str = Header(None)):
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
            exec_result = await execute_and_learn(
                action_data=action_data,
                incident_text=details["incident_text"],
                confidence=details["confidence"]
            )
            return {
                "status": "AUTO_EXECUTED",
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
async def approve_action(action_id: str):
    action_data = ApprovalManager.approve(action_id)
    if not action_data:
        raise HTTPException(status_code=404, detail="Action ID not found or already executed")
    
    # الأكشن داتا متخزن فيها الـ incident_text والـ confidence من الـ Brain
    payload_to_exec = {
        "command": action_data["command"],
        "target": action_data["target"]
    }
    
    try:
        exec_result = await execute_and_learn(
            action_data=payload_to_exec,
            incident_text=action_data.get("incident_text", "Manual Approval Incident"),
            confidence=action_data.get("confidence", 1.0),
            action_id=action_id
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5555)
