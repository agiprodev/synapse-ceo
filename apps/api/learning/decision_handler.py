import uuid
from apps.api.learning.policy import evaluate_policy

class DecisionHandler:
    @staticmethod
    def process_ai_verdict(customer_id: str, agent_id: str, ai_result: dict):
        """
        يستلم نتيجة الـ AI (Gemini) ويمررها عبر فلتر الـ Policy
        """
        action = ai_result.get("action", "IGNORE")
        confidence = ai_result.get("confidence", 0.0)
        
        # مراجعة الدستور
        policy_verdict = evaluate_policy(action, confidence)
        
        decision_id = f"dec_{uuid.uuid4().hex[:8]}"
        
        return {
            "decision_id": decision_id,
            "customer_id": customer_id,
            "agent_id": agent_id,
            "action": action,
            "status": policy_verdict["status"],
            "message": policy_verdict["reason"],
            "is_autonomous": policy_verdict["allowed"],
            "metadata": {
                "confidence": confidence,
                "severity": "LOW" if policy_verdict["allowed"] else "MEDIUM/HIGH"
            }
        }

# مثال للاختبار السريع
if __name__ == "__main__":
    handler = DecisionHandler()
    # تجربة قرار آمن بنسبة ثقة عالية
    print(handler.process_ai_verdict("cust_1", "srv_1", {"action": "RESTART_DOCKER", "confidence": 0.95}))
    # تجربة قرار يحتاج موافقة
    print(handler.process_ai_verdict("cust_1", "srv_1", {"action": "SCALE_UP", "confidence": 0.90}))
