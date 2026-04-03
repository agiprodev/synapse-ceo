from apps.api.actions.pending import ApprovalManager
from apps.api.actions.policy import PolicyEngine
from apps.api.actions.safety import SafetyGuard
from apps.api.learning.retrieval import MemoryRetrieval

class DecisionEngine:
    @staticmethod
    def process_incident(incident_data):
        action = "RESTART_DOCKER"
        target = "frappe-app-v1"
        confidence = 0.94
        risk = "LOW"

        incident_text = f"Agent={incident_data.get('agent_id')} | CPU={incident_data.get('cpu_percent')} | Logs={incident_data.get('recent_logs')}"

        memory = MemoryRetrieval()
        history_count = memory.get_success_count(incident_text)
        experience_context = memory.build_experience_context(incident_text)

        if SafetyGuard.is_emergency_stop():
            mode = "REQUIRES_APPROVAL"
            reason = "🔴 Emergency Stop Active: Auto-pilot disabled by Administrator."
        else:
            mode = PolicyEngine.get_execution_mode(action, confidence, risk, history_count)
            reason = (
                f"⚡ Auto-pilot: {history_count} similar successful incidents found.\n{experience_context}"
                if mode == "AUTO_PILOT"
                else f"⚠️ Manual approval required. Similar successful incidents found: {history_count}.\n{experience_context}"
            )

        decision = {
            "action": action, "target": target, "confidence": confidence,
            "mode": mode, "reason": reason, "history_count": history_count, "incident_text": incident_text
        }

        if mode == "AUTO_PILOT":
            return {"status": "EXECUTING_NOW", "details": decision}
        else:
            action_id = ApprovalManager.create_pending({
                "command": action,
                "target": target,
                "incident_text": incident_text,
                "confidence": confidence,
                "customer_id": incident_data.get("customer_id"),
                "agent_id": incident_data.get("agent_id"),
            })
            return {"status": "PENDING_APPROVAL", "action_id": action_id, "details": decision}
