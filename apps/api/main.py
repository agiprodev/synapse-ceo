from fastapi import FastAPI
import httpx, docker, os
from orchestrator import run_strategic_meeting
from apps.api.aws_sns import router as aws_sns_router

app = FastAPI(title="Synapse Boardroom V2")
app.include_router(aws_sns_router)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

try:
    docker_client = docker.from_env()
except:
    docker_client = None

@app.post("/decide/restart/{container_id}")
async def handle_incident(container_id: str):
    if not docker_client:
        return {"error": "Docker Socket not accessible"}

    container = docker_client.containers.get(container_id)
    logs = container.logs(tail=20).decode('utf-8')
    
    # حساب سريع للـ CPU
    stats = container.stats(stream=False)
    cpu_pct = 0.0
    try:
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats.get('precpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0)
        sys_delta = stats['cpu_stats'].get('system_cpu_usage', 0) - stats.get('precpu_stats', {}).get('system_cpu_usage', 0)
        if sys_delta > 0: cpu_pct = (cpu_delta / sys_delta) * 100.0
    except: pass

    # 🧠 استدعاء الاجتماع الاستراتيجي (المخ + الذاكرة + فرايبي)
    meeting = run_strategic_meeting(f"High Load on {container_id}. Logs: {logs}", cpu_pct)
    
    # 📱 إرسال التقرير الذكي لتليجرام
    report = (
        f"🛡️ *Synapse CEO: Decision Report*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 *Container:* `{container_id}`\n"
        f"📈 *CPU Load:* `{cpu_pct:.1f}%`\n"
        f"📜 *History:* {'✅ Data Found' if meeting['history_found'] else '🆕 First Time'}\n\n"
        f"🏆 *Final Action:* *{meeting['target_action']}*\n"
        f"💬 *Reason:* _{meeting['ceo_summary']}_\n"
        f"🎯 *Confidence:* `{int(meeting['confidence']*100)}%`"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    keyboard = {"inline_keyboard": [[
        {"text": f"🚀 Execute {meeting['target_action']}", "callback_data": f"exec_{meeting['target_action']}_{container_id}"},
        {"text": "🔇 Ignore", "callback_data": "dismiss"}
    ]]}
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": CHAT_ID, 
            "text": report, 
            "parse_mode": "Markdown", 
            "reply_markup": keyboard
        })

    return {"status": "Strategic Decision Dispatched", "action": meeting['target_action']}

@app.on_event("startup")
async def startup():
    print("🚀 Synapse Boardroom V2 (Memory + Enterprise) is online.")
