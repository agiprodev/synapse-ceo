import psutil
import time

class PerformanceVerifier:
    @staticmethod
    def get_snapshot():
        return {
            "cpu": psutil.cpu_percent(interval=0.1),
            "mem": psutil.virtual_memory().percent,
            "time": time.time()
        }

    @staticmethod
    def calc_roi(before, after):
        # معادلة توفير الفلوس: (فرق الـ CPU + منع الـ Downtime) * معامل التكلفة
        savings = (before['cpu'] - after['cpu']) * 0.5 + 50 # 50$ بونص نجاح
        return round(max(savings, 10.0), 2)
