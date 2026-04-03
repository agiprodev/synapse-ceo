from enum import Enum
from pydantic import BaseModel
from typing import List, Dict, Optional

class ActionSeverity(Enum):
    LOW = "low"      # Restart container, Clear logs
    MEDIUM = "medium" # Scale Up, Resource Reallocation
    HIGH = "high"    # Delete, Database migration, Infrastructure change

class PolicyRule(BaseModel):
    action_type: str
    severity: ActionSeverity
    auto_approve: bool
    max_cost_impact: float # $ USD

# الدستور الافتراضي للنظام
DEFAULT_POLICIES = {
    "RESTART_DOCKER": PolicyRule(action_type="RESTART", severity=ActionSeverity.LOW, auto_approve=True, max_cost_impact=0.0),
    "CLEANUP_LOGS": PolicyRule(action_type="CLEANUP", severity=ActionSeverity.LOW, auto_approve=True, max_cost_impact=0.0),
    "SCALE_UP": PolicyRule(action_type="SCALE", severity=ActionSeverity.MEDIUM, auto_approve=False, max_cost_impact=50.0),
    "TERMINATE_INSTANCE": PolicyRule(action_type="TERMINATE", severity=ActionSeverity.HIGH, auto_approve=False, max_cost_impact=0.0)
}

def evaluate_policy(action: str, confidence: float, estimated_cost: float = 0.0) -> dict:
    """
    تقييم القرار بناءً على القوانين:
    - هل مسموح أوتوماتيكياً؟
    - هل يحتاج موافقة بشرية؟
    - هل الثقة (Confidence) كافية؟
    """
    rule = DEFAULT_POLICIES.get(action)
    
    # إذا كان الفعل غير معرف، نعتبره عالي الخطورة للأمان
    if not rule:
        return {"allowed": False, "reason": "Unknown action, safety first.", "status": "PENDING_APPROVAL"}

    # شرط الثقة الأدنى للتنفيذ الآلي
    MIN_CONFIDENCE = 0.85

    if rule.auto_approve and confidence >= MIN_CONFIDENCE and estimated_cost <= rule.max_cost_impact:
        return {"allowed": True, "reason": "Policy approved: Low risk action.", "status": "EXECUTING"}
    
    return {
        "allowed": False, 
        "reason": "Policy Guardrail: Requires human approval or higher confidence.", 
        "status": "PENDING_APPROVAL"
    }
