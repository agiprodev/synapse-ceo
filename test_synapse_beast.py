import asyncio
import httpx

async def test_full_flow():
    BASE_URL = "http://127.0.0.1:5555/v1"
    async with httpx.AsyncClient(timeout=30.0) as client:
        payload = {
            "customer_id": "cust_001",
            "agent_id": "srv-prod-01",
            "cpu_percent": 98.5,
            "mem_percent": 85.0,
            "disk_usage": 40.0,
            "recent_logs": "ERROR: CPU Spike detected",
            "metadata": {}
        }
        
        print("📡 Sending Full Metrics to Beast...")
        try:
            response = await client.post(f"{BASE_URL}/decide", json=payload, headers={"x-api-key": "test_key"})
            decision = response.json()
            
            if decision.get("status") == "AUTO_EXECUTED":
                print(f"\n✈️ [AUTO-PILOT ENGAGED]")
                print(f"✅ Reason: {decision.get('reason')}")
                print(f"⚙️ Agent Output: {decision.get('agent_response')}")
            elif decision.get("action_id"):
                print(f"\n🚀 AI Verdict: {decision.get('action')} (PENDING APPROVAL)")
                print(f"🆔 [REAL ID]: {decision.get('action_id')}")
                print(f"👉 COPY AND RUN THIS COMMAND:\ncurl -X POST {BASE_URL}/approve/{decision.get('action_id')}")
            else:
                print(f"❌ Unhandled Server Response: {decision}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
