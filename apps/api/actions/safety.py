import os

class SafetyGuard:
    @staticmethod
    def is_emergency_stop():
        # لو فيه ملف اسمه STOP موجود، عطل كل الأوتو بايلوت
        return os.path.exists("EMERGENCY_STOP.lock")

    @staticmethod
    def trigger_stop():
        open("EMERGENCY_STOP.lock", "a").close()
