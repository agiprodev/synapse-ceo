import os, json
from google import genai
from memory.service import MemoryService
from memory.provider import GeminiEmbeddingProvider
from memory.frappe_provider import FrappeProvider

# Config
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

# Initialize
try:
    # استخدام الموديل الأضمن في الـ Embeddings
    embedder = GeminiEmbeddingProvider(client, model="text-embedding-004")
    memory = MemoryService(qdrant_url="http://qdrant:6333", embedding_provider=embedder)
    frappe = FrappeProvider()
except Exception as e:
    print(f"⚠️ Init Warning: {e}")

def get_structured_ai_analysis(role: str, context: str):
    # استخدام 1.5 flash لأنه أهدى في الـ Quota
    prompt = f"You are a {role}. Context: {context}. Return ONLY JSON with: 'reason', 'confidence', 'suggested_action'."
    try:
        res = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt, 
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(res.text)
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return {"reason": "Quota Fallback", "confidence": 0.5, "suggested_action": "IGNORE"}

def log_to_enterprise(meeting_result):
    try:
        # تأكد من أن يوزر الـ API له صلاحية على Communication
        payload = {
            "subject": f"AI Decision: {meeting_result['target_action']}",
            "content": f"CEO Summary: {meeting_result['ceo_summary']}\nConfidence: {meeting_result['confidence']}",
            "sent_or_received": "Sent",
            "communication_type": "Communication"
        }
        return frappe.post_log("Communication", payload)
    except Exception as e:
        print(f"⚠️ Frappe Sync Failed: {e}")
        return None

def run_strategic_meeting(incident_summary: str, current_cpu: float):
    past_incidents = []
    try:
        past_incidents = memory.search_similar(incident_summary, limit=2)
    except: pass

    history_context = "\n".join([f"- Past: {h['text']}" for h in past_incidents]) if past_incidents else "No History."

    context = f"Current: {incident_summary}. History: {history_context}"
    cto_res = get_structured_ai_analysis("CTO", context)
    ceo_res = get_structured_ai_analysis("CEO", f"CTO says: {cto_res['reason']}. History: {history_context}")

    result = {
        "target_action": ceo_res.get('suggested_action', 'IGNORE'),
        "ceo_summary": ceo_res.get('reason', 'Analyzed with fallback'),
        "confidence": ceo_res.get('confidence', 0.9),
        "history_found": len(past_incidents) > 0
    }

    try:
        memory.upsert_incident(incident_summary, {"cpu": current_cpu, "decision": result['target_action']})
    except: pass

    log_to_enterprise(result)
    return result
