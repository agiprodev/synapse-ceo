from fastapi import FastAPI, Request, HTTPException
from agent.executor import ActionExecutor
import uvicorn

app = FastAPI()

@app.post("/execute")
async def handle_remote_action(request: Request):
    data = await request.json()
    payload = data.get("payload")
    signature = data.get("signature")
    
    if not payload or not signature:
        raise HTTPException(status_code=400, detail="Missing payload or signature")
    
    # تنفيذ الأمر (الـ Executor هيتحقق من التوقيع داخلياً)
    result = ActionExecutor.run(payload, signature)
    
    if result.get("status") == "CRITICAL_ERROR":
        raise HTTPException(status_code=403, detail="Security Breach: Invalid Signature")
        
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999) # بورت الأوامر المنفصل
