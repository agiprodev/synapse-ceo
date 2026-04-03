import subprocess
from apps.api.security.signer import verify_action

# ⚡ الآن: أوامر حقيقية تغير حالة السيرفر
ALLOWED_COMMANDS = {
    "RESTART_DOCKER": ["docker", "restart"],
    "CLEAN_TMP": ["find", "/tmp", "-type", "f", "-mmin", "+60", "-delete"],
    "RESTART_SERVICE": ["systemctl", "restart"]
}

class ActionExecutor:
    @staticmethod
    def run(action_request: dict, sig: str):
        if not verify_action(action_request, sig):
            return {"status": "CRITICAL_ERROR", "message": "INVALID_SIGNATURE"}

        cmd_key = action_request.get("command")
        target = action_request.get("target")

        if cmd_key not in ALLOWED_COMMANDS:
            return {"status": "DENIED", "message": f"Command {cmd_key} not authorized"}

        full_cmd = ALLOWED_COMMANDS[cmd_key] + [target]

        try:
            # تنفيذ حقيقي ⛓️
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
            return {
                "status": "SUCCESS" if result.returncode == 0 else "FAILED",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "return_code": result.returncode
            }
        except Exception as e:
            return {"status": "SYSTEM_ERROR", "message": str(e)}
