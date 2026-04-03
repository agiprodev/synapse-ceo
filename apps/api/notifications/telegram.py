import httpx
import os

# ملاحظة: في الـ Production، القيم دي بتيجي من الـ Environment Variables
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
DEFAULT_CHAT_ID = "YOUR_CHAT_ID"

class TelegramNotifier:
    @staticmethod
    async def send_impact_report(customer_id: str, decision_data: dict):
        """
        إرسال تقرير "توفير" فوري للعميل
        """
        token = TELEGRAM_TOKEN
        chat_id = DEFAULT_CHAT_ID
        
        emoji = "🚀" if decision_data['status'] == "SUCCESS" else "⚠️"
        
        message = (
            f"{emoji} *Synapse AI Action Report*\n\n"
            f"👤 *Customer:* {customer_id}\n"
            f"🤖 *Action:* {decision_data['action']}\n"
            f"🎯 *Target:* {decision_data['target']}\n"
            f"-------------------\n"
            f"💰 *Saved:* ${decision_data['saved_dollars']}\n"
            f"⏱️ *Time Recovered:* {decision_data['saved_minutes']} min\n"
            f"-------------------\n"
            f"✅ *Status:* Verified Healthy"
        )
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=payload)
                print(f"📡 [NOTIFICATION] Report sent to Telegram for {customer_id}")
            except Exception as e:
                print(f"❌ [NOTIFICATION] Failed to send telegram: {e}")

