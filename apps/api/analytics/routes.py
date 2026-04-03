from fastapi import APIRouter

router = APIRouter(prefix="/v1/analytics")

@router.get("/dashboard/{customer_id}")
async def get_dashboard_data(customer_id: str):
    return {
        "hero_kpis": {
            "money_saved": 4872.0,
            "hours_saved": 48
        },
        "risk_status": "LOW"
    }
