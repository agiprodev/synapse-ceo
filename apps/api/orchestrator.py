import os
from google import genai
from typing import TypedDict

class State(TypedDict):
    incident: str
    cto_opinion: str
    cfo_opinion: str
    final_decision: str
    action_button: str

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def get_ai_response(role, prompt):
    # Prompt معدل ليعطي تحليل عميق ومختصر في نفس الوقت
    full_prompt = f"You are a {role}. Context: {prompt}. Analyze logs if any and give 1 short technical sentence about the root cause and solution."
    try:
        return client.models.generate_content(model='gemini-2.5-flash', contents=full_prompt).text.strip()
    except Exception as e:
        return f"GenAI Error: {str(e)}"

def get_action_button(prompt):
    full_prompt = f"Context: {prompt}. Based on this, reply ONLY with ONE word: [RESTART, CLEAR_CACHE, IGNORE]."
    try:
        res = client.models.generate_content(model='gemini-2.5-flash', contents=full_prompt).text.strip().upper()
        if "RESTART" in res: return "RESTART"
        if "CLEAR" in res or "CACHE" in res: return "CLEAR_CACHE"
        return "IGNORE"
    except:
        return "IGNORE"

def cto_agent(state: State):
    state['cto_opinion'] = get_ai_response("Cloud CTO", f"Technical Context: {state['incident']}")
    return state

def cfo_agent(state: State):
    state['cfo_opinion'] = get_ai_response("Financial Officer", f"CTO says: {state['cto_opinion']}. Financial impact?")
    return state

def ceo_agent(state: State):
    # الـ CEO هنا بيلخص المشكلة والحل بناءً على كلام الخبراء
    state['final_decision'] = get_ai_response("CEO", f"CTO: {state['cto_opinion']}, CFO: {state['cfo_opinion']}. Give final order.")
    state['action_button'] = get_action_button(state['final_decision'])
    return state
