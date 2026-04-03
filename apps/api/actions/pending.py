import uuid

# مخزن مؤقت في الذاكرة (للمحاكاة)
PENDING_ACTIONS = {}

class ApprovalManager:
    @staticmethod
    def create_pending(action_data: dict):
        action_id = str(uuid.uuid4())[:8]
        PENDING_ACTIONS[action_id] = {
            "id": action_id,
            "data": action_data,
            "status": "PENDING"
        }
        return action_id

    @staticmethod
    def get_action(action_id: str):
        return PENDING_ACTIONS.get(action_id)

    @staticmethod
    def approve(action_id: str):
        if action_id in PENDING_ACTIONS:
            PENDING_ACTIONS[action_id]["status"] = "APPROVED"
            return PENDING_ACTIONS[action_id]["data"]
        return None
