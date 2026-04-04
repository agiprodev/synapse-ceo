import json
import logging
import os
import socket
import subprocess
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque
from urllib import request

logger = logging.getLogger("synapse_pulse")


@dataclass
class PulseConfig:
    slack_webhook: str | None
    check_interval_secs: int = 5
    cpu_window: int = 3
    alert_cooldown_secs: int = 60
    cpu_warning_threshold: float = 90.0
    cpu_rise_critical_threshold: float = 20.0
    mem_critical_threshold: float = 80.0
    http_timeout_secs: int = 5
    remediation_command: str | None = None
    remediation_timeout_secs: int = 30
    enable_autonomous_remediation: bool = False
    executor_workers: int = 4
    host: str = socket.gethostname()
    environment: str = "prod"


@dataclass
class Alert:
    severity: str
    reasoning: str
    action: str
    remediation_cmd: str | None = None


class SynapsePulse:
    def __init__(self, config: PulseConfig):
        self.config = config
        self.cpu_history: Deque[float] = deque(maxlen=config.cpu_window)
        self.last_alert_ts = 0.0
        self._executor = ThreadPoolExecutor(max_workers=max(1, config.executor_workers))

    def analyze(self, cpu_now: float, mem_percent: float) -> Alert | None:
        self.cpu_history.append(cpu_now)
        if len(self.cpu_history) < self.config.cpu_window:
            return None

        recent = list(self.cpu_history)
        cpu_rise = recent[-1] - recent[0]

        if cpu_rise >= self.config.cpu_rise_critical_threshold and mem_percent > self.config.mem_critical_threshold:
            return Alert(
                severity="🔴 CRITICAL",
                reasoning=(
                    f"CPU jumped {cpu_rise:.1f}% in {self.config.cpu_window * self.config.check_interval_secs}s "
                    f"(now {cpu_now:.1f}%) while Memory is at {mem_percent:.1f}%. "
                    "Pattern matches Traffic Surge → likely crash in ~60s."
                ),
                action="Auto-scale target service or restart heavy worker pool.",
                remediation_cmd=self.config.remediation_command,
            )

        if cpu_now >= self.config.cpu_warning_threshold:
            return Alert(
                severity="🟡 WARNING",
                reasoning=(
                    f"CPU sustained at {cpu_now:.1f}%. Memory stable at {mem_percent:.1f}%. "
                    "Possible runaway process or lock contention."
                ),
                action="Investigate top processes and thread contention.",
            )

        return None

    def _build_message(self, alert: Alert) -> dict:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return {
            "text": (
                f"*Rises Synapse PRO Alert* | {now}\n"
                f"Host: `{self.config.host}` | Env: `{self.config.environment}`\n"
                f"{alert.severity}\n"
                f"*Reasoning:* {alert.reasoning}\n"
                f"*Action:* {alert.action}"
            )
        }

    def send_slack(self, alert: Alert) -> None:
        if not self.config.slack_webhook:
            logger.info("Slack webhook is not configured; skipping notification")
            return

        payload = json.dumps(self._build_message(alert)).encode("utf-8")
        req = request.Request(
            self.config.slack_webhook,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.config.http_timeout_secs) as response:
            if response.status >= 400:
                raise RuntimeError(f"Slack webhook failed with status={response.status}")

    def send_slack_async(self, alert: Alert) -> None:
        self._executor.submit(self.send_slack, alert)

    def execute_remediation(self, alert: Alert) -> None:
        if alert.severity != "🔴 CRITICAL":
            return
        if not self.config.enable_autonomous_remediation:
            return
        if not alert.remediation_cmd:
            logger.warning("Critical alert detected but no remediation command configured")
            return

        completed = subprocess.run(
            alert.remediation_cmd,
            shell=True,
            timeout=self.config.remediation_timeout_secs,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            logger.info("Remediation command succeeded: %s", alert.remediation_cmd)
            return
        logger.error(
            "Remediation command failed (code=%s): %s | stderr=%s",
            completed.returncode,
            alert.remediation_cmd,
            completed.stderr.strip(),
        )

    def execute_remediation_async(self, alert: Alert) -> None:
        self._executor.submit(self.execute_remediation, alert)

    def run_forever(self) -> None:
        logger.info("Starting Synapse Pulse monitor on host=%s env=%s", self.config.host, self.config.environment)

        try:
            import psutil
        except ModuleNotFoundError as exc:
            raise RuntimeError("psutil is required to run SynapsePulse monitoring loop") from exc

        while True:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            alert = self.analyze(cpu_now=cpu, mem_percent=mem)
            now = time.time()

            if alert and (now - self.last_alert_ts) > self.config.alert_cooldown_secs:
                try:
                    self.send_slack_async(alert)
                    self.execute_remediation_async(alert)
                    self.last_alert_ts = now
                    logger.info("Alert dispatched: %s", alert.severity)
                except Exception as exc:  # best-effort notifier
                    logger.exception("Failed to dispatch alert/remediation: %s", exc)

            time.sleep(self.config.check_interval_secs)


def load_config() -> PulseConfig:
    return PulseConfig(
        slack_webhook=os.getenv("SYNAPSE_SLACK_WEBHOOK"),
        check_interval_secs=int(os.getenv("SYNAPSE_CHECK_INTERVAL", "5")),
        cpu_window=int(os.getenv("SYNAPSE_CPU_WINDOW", "3")),
        alert_cooldown_secs=int(os.getenv("SYNAPSE_ALERT_COOLDOWN", "60")),
        cpu_warning_threshold=float(os.getenv("SYNAPSE_CPU_WARNING", "90")),
        cpu_rise_critical_threshold=float(os.getenv("SYNAPSE_CPU_RISE_CRITICAL", "20")),
        mem_critical_threshold=float(os.getenv("SYNAPSE_MEM_CRITICAL", "80")),
        http_timeout_secs=int(os.getenv("SYNAPSE_HTTP_TIMEOUT", "5")),
        remediation_command=os.getenv("SYNAPSE_REMEDIATION_COMMAND"),
        remediation_timeout_secs=int(os.getenv("SYNAPSE_REMEDIATION_TIMEOUT", "30")),
        enable_autonomous_remediation=os.getenv("SYNAPSE_ENABLE_REMEDIATION", "false").lower() == "true",
        executor_workers=int(os.getenv("SYNAPSE_EXECUTOR_WORKERS", "4")),
        host=os.getenv("SYNAPSE_HOST", socket.gethostname()),
        environment=os.getenv("SYNAPSE_ENV", "prod"),
    )


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("SYNAPSE_LOG_LEVEL", "INFO").upper())
    SynapsePulse(load_config()).run_forever()
