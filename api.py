import asyncio
import json
from pathlib import Path

import psutil
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from agent.synapse_pulse import SynapsePulse, load_config

app = FastAPI(title="Rises Synapse PRO API")
DASHBOARD_PATH = Path(__file__).with_name("dashboard.html")


@app.get("/")
async def get_dashboard() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))


@app.get("/stream")
async def stream_metrics() -> StreamingResponse:
    async def event_generator():
        monitor = SynapsePulse(load_config())
        psutil.cpu_percent()

        while True:
            await asyncio.sleep(1)

            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent

            metrics_data = {"type": "metrics", "cpu": cpu, "mem": mem}
            yield f"data: {json.dumps(metrics_data)}\n\n"

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5555)
