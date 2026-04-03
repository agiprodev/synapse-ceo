class PolicyEngine:
    AUTO_ALLOWLIST = ["RESTART_DOCKER", "CLEAN_TMP", "RESTART_SERVICE"]
    CONFIDENCE_THRESHOLD = 0.90
    
    @staticmethod
    def get_execution_mode(action, confidence, risk_level, history_success_count):
        # شروط الـ Auto-Pilot الصارمة
        is_allowed = action in PolicyEngine.AUTO_ALLOWLIST
        high_confidence = confidence >= PolicyEngine.CONFIDENCE_THRESHOLD
        low_risk = risk_level == "LOW"
        proven_track_record = history_success_count >= 3 # لازم يكون نجح 3 مرات قبل كدة

        if is_allowed and high_confidence and low_risk and proven_track_record:
            return "AUTO_PILOT"
        return "REQUIRES_APPROVAL"
