import httpx
import asyncio
from apps.api.security.signer import sign_action

async def test_bite():
    print("🧠 [BRAIN] Deciding to restart docker container...")
    
    payload = {
        "command": "RESTART_DOCKER",
        "target": "frappe-app-v1"
    }
    
    # التوقيع الرقمي (الختم الملكي)
    signature = sign_action(payload)
    
    async with httpx.AsyncClient() as client:
        print("📡 [NETWORK] Sending signed action to Agent...")
        try:
            response = await client.post(
                "http://127.0.0.1:9999/execute",
                json={"payload": payload, "signature": signature}
            )
            
            if response.status_code == 200:
                res = response.json()
                print(f"✅ [AGENT] Response: {res['status']} | Output: {res.get('stdout')}")
            else:
                print(f"❌ [AGENT] Failed! {response.status_code}: {response.text}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_bite())
