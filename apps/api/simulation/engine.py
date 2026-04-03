import asyncio
import random
from apps.api.notifications.telegram import TelegramNotifier

class IncidentSimulator:
    def __init__(self, agent_id: str, customer_id: str = "cust_001"):
        self.agent_id = agent_id
        self.customer_id = customer_id

    async def run_full_scenario(self):
        """
        تشغيل السيناريو الكامل: انفجار -> حل -> إشعار توفير
        """
        print(f"🔥 [SIMULATOR] Starting Chaos on {self.agent_id}")
        await asyncio.sleep(2) # محاكاة وقت التحليل
        
        # بيانات القرار اللي الـ AI خده
        decision_impact = {
            "action": "RESTART_DOCKER",
            "target": self.agent_id,
            "status": "SUCCESS",
            "saved_dollars": 9.0,
            "saved_minutes": 18
        }
        
        # إرسال التقرير فوراً للعميل
        await TelegramNotifier.send_impact_report(self.customer_id, decision_impact)
        return decision_impact
