import requests
import os

class FrappeProvider:
    def __init__(self):
        self.url = os.getenv("FRAPPE_URL")
        self.api_key = os.getenv("FRAPPE_API_KEY")
        self.api_secret = os.getenv("FRAPPE_API_SECRET")
        self.headers = {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }

    def post_log(self, doctype, data):
        # محاولة إرسال البيانات لـ Frappe
        endpoint = f"{self.url}/api/resource/{doctype}"
        try:
            response = requests.post(endpoint, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Frappe Integration Error: {e}")
            return None
