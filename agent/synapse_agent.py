import os
import socket
import time
from dataclasses import dataclass

import httpx

from agent.executor import ActionExecutor


@dataclass
class AgentConfig:
    api_base_url: str
    tenant_id: str
    hostname: str
    environment: str
    heartbeat_interval_secs: int = 15
    poll_interval_secs: int = 5
    request_timeout_secs: int = 20


class SynapseAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id: str | None = None

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.config.api_base_url, timeout=self.config.request_timeout_secs)

    def register(self) -> None:
        payload = {
            "tenant_id": self.config.tenant_id,
            "hostname": self.config.hostname,
            "environment": self.config.environment,
            "metadata": {
                "agent_version": "v0.1",
                "mode": "reverse_tunnel_pull",
            },
        }

        with self._client() as client:
            response = client.post("/v1/agents/register", json=payload)
            response.raise_for_status()
            data = response.json()

        self.agent_id = data["agent_id"]
        print(f"[REGISTERED] tenant={self.config.tenant_id} agent_id={self.agent_id} hostname={self.config.hostname}")

    def heartbeat(self) -> None:
        if not self.agent_id:
            raise RuntimeError("Agent is not registered")

        payload = {
            "tenant_id": self.config.tenant_id,
            "agent_id": self.agent_id,
            "metrics": {
                "ts": int(time.time()),
            },
        }
        with self._client() as client:
            response = client.post("/v1/agents/heartbeat", json=payload)
            response.raise_for_status()

    def fetch_next_command(self) -> dict:
        if not self.agent_id:
            raise RuntimeError("Agent is not registered")

        params = {
            "tenant_id": self.config.tenant_id,
            "agent_id": self.agent_id,
        }

        with self._client() as client:
            response = client.get("/v1/agents/commands/next", params=params)
            response.raise_for_status()
            return response.json()

    def ack_command(self, command_id: str, status: str, message: str | None, result_payload: dict | None) -> None:
        if not self.agent_id:
            raise RuntimeError("Agent is not registered")

        payload = {
            "tenant_id": self.config.tenant_id,
            "agent_id": self.agent_id,
            "status": status,
            "message": message,
            "result_payload": result_payload,
        }

        with self._client() as client:
            response = client.post(f"/v1/agents/commands/{command_id}/ack", json=payload)
            response.raise_for_status()

    def run_forever(self) -> None:
        print("[BOOT] Starting Synapse Edge Agent...")

        while True:
            try:
                if not self.agent_id:
                    self.register()

                self.heartbeat()

                command = self.fetch_next_command()
                if command.get("status") == "COMMAND_DISPATCHED":
                    command_id = command["command_id"]
                    payload = command["payload"]
                    signature = command["signature"]

                    print(f"[COMMAND] id={command_id} payload={payload}")
                    result = ActionExecutor.run(payload, signature)
                    result_status = (result.get("status") or "FAILED").upper()

                    ack_status = "success" if result_status == "SUCCESS" else "failed"
                    ack_message = result.get("message") or result.get("stderr") or result_status

                    self.ack_command(
                        command_id=command_id,
                        status=ack_status,
                        message=ack_message,
                        result_payload=result,
                    )
                    print(f"[ACK] id={command_id} status={ack_status}")
                else:
                    print("[IDLE] no pending commands")

                time.sleep(self.config.poll_interval_secs)

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                print(f"[HTTP_ERROR] status={status} body={exc.response.text}")

                # 403 غالباً tenant suspended أو access issue → نهدّي الحلقة شوية
                if status in {401, 403}:
                    time.sleep(max(self.config.poll_interval_secs, 15))
                elif status == 404:
                    # Agent state ممكن يكون reset في الـ backend، نسجل تاني
                    self.agent_id = None
                    time.sleep(3)
                else:
                    time.sleep(self.config.poll_interval_secs)

            except Exception as exc:
                print(f"[ERROR] {exc}")
                time.sleep(self.config.poll_interval_secs)


def load_config() -> AgentConfig:
    tenant_id = os.getenv("SYNAPSE_TENANT_ID")
    if not tenant_id:
        raise RuntimeError("Missing required env var: SYNAPSE_TENANT_ID")

    return AgentConfig(
        api_base_url=os.getenv("SYNAPSE_API_BASE_URL", "http://localhost:5555"),
        tenant_id=tenant_id,
        hostname=os.getenv("SYNAPSE_AGENT_HOSTNAME", socket.gethostname()),
        environment=os.getenv("SYNAPSE_AGENT_ENV", "prod"),
        heartbeat_interval_secs=int(os.getenv("SYNAPSE_HEARTBEAT_SECS", "15")),
        poll_interval_secs=int(os.getenv("SYNAPSE_POLL_SECS", "5")),
        request_timeout_secs=int(os.getenv("SYNAPSE_HTTP_TIMEOUT_SECS", "20")),
    )


if __name__ == "__main__":
    cfg = load_config()
    SynapseAgent(cfg).run_forever()
