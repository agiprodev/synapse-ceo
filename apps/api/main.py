from fastapi import FastAPI
import httpx
import docker
import asyncio
import os
from orchestrator import cto_agent, cfo_agent, ceo_agent

app = FastAPI(title="Synapse CEO Kernel")

# 🔒 سحب المفاتيح من البيئة بأمان
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CPU_THRESHOLD = 80.0

try: docker_client = docker.from_env()
except: docker_client = None

def get_container_metrics(container):
    try:
        stats = container.stats(stream=False)
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats.get('precpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0)
        sys_delta = stats['cpu_stats'].get('system_cpu_usage', 0) - stats.get('precpu_stats', {}).get('system_cpu_usage', 0)
        cpu_percent = (cpu_delta / sys_delta) * stats['cpu_stats'].get('online_cpus', 1) * 100.0 if sys_delta > 0 else 0.0
        mem_usage = stats['memory_stats'].get('usage', 0) / (1024 * 1024)
        return cpu_percent, mem_usage
    except: return 0.0, 0.0

def get_container_logs(container):
    try: return container.logs(tail=10).decode('utf-8') or "No logs."
    except: return "No logs available."

async def send_dynamic_report(c_name: str, report: str, action: str):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    if action == "RESTART":
        buttons = [[{"text": "🔄 Approve Restart", "callback_data": f"restart_{c_name}"}, {"text": "❌ Dismiss", "callback_data": f"dismiss_{c_name}"}]]
    elif action == "CLEAR_CACHE":
        buttons = [[{"text": "🧹 Clear Cache", "callback_data": f"cache_{c_name}"}, {"text": "❌ Dismiss", "callback_data": f"dismiss_{c_name}"}]]
    else: 
        buttons = [[{"text": "✅ Acknowledge & Dismiss", "callback_data": f"dismiss_{c_name}"}]]
        
    await httpx.AsyncClient().post(url, json={"chat_id": CHAT_ID, "text": report, "parse_mode": "Markdown", "reply_markup": {"inline_keyboard": buttons}})

async def trigger_ai_deliberation(c_name, cpu, mem):
    container = docker_client.containers.get(c_name)
    logs = get_container_logs(container)
    stats_str = f"CPU: {cpu:.2f}% | RAM: {mem:.2f}MB"
    
    initial_state = {
        "incident": f"Target: {c_name}\nStats: {stats_str}\nLogs:\n{logs}",
        "cto_opinion": "", "cfo_opinion": "", "final_decision": "", "action_button": ""
    }
    
    s1 = cto_agent(initial_state)
    s2 = cfo_agent(s1)
    final_state = ceo_agent(s2)
    
    report = (
        f"🚨 *AI SYSTEM DIAGNOSTIC*\n\n"
        f"📦 *Container:* `{c_name}`\n"
        f"📊 *Metrics:* `{stats_str}`\n\n"
        f"👨‍💻 *CTO:* _{final_state['cto_opinion']}_\n"
        f"🧠 *CEO Order:* *{final_state['final_decision']}*\n"
    )
    await send_dynamic_report(c_name, report, final_state['action_button'])

async def telegram_poller():
    if not TELEGRAM_TOKEN: return
    last_id = 0
    while True:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_id+1}&timeout=10")
                for up in res.json().get("result", []):
                    last_id = up["update_id"]
                    if "callback_query" in up:
                        cb = up["callback_query"]
                        cb_data = cb["data"]
                        c_n = cb_data.split("_")[1]
                        
                        if cb_data.startswith("restart_"):
                            docker_client.containers.get(c_n).restart()
                            msg = f"✅ *Action:* `{c_n}` restarted by CEO."
                        elif cb_data.startswith("cache_"):
                            docker_client.containers.get(c_n).exec_run("echo 'Cache Cleared'") 
                            msg = f"🧹 *Action:* `{c_n}` cache cleared by CEO."
                        elif cb_data.startswith("dismiss_"):
                            msg = f"✅ *Action:* Alert for `{c_n}` dismissed."
                            
                        await client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        except: pass
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(telegram_poller())

@app.get("/")
async def root(): return {"status": "Synapse Dynamic AI Active (Secured)"}

@app.post("/decide/restart/{container_id}")
async def manual_trigger(container_id: str):
    cpu, mem = get_container_metrics(docker_client.containers.get(container_id))
    await trigger_ai_deliberation(container_id, cpu, mem)
    return {"status": "Dynamic AI Deliberation Sent"}
