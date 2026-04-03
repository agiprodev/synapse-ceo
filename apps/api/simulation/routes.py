from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/v1/simulation")

@router.post("/trigger/{agent_id}")
async def start_demo(agent_id: str, background_tasks: BackgroundTasks):
    return {
        "message": f"Demo Incident triggered on {agent_id}",
        "status": "CHAOS_MODE_ACTIVE"
    }
