import json

def get_total_savings():
    total = 0.0
    try:
        with open("beast_history.log", "r") as f:
            for line in f:
                entry = json.loads(line)
                total += entry.get("impact_dollars", 0)
    except FileNotFoundError:
        return 0.0
    return round(total, 2)

print(f"\n🏆 --- SYNAPSE BEAST DASHBOARD --- 🏆")
print(f"💰 Total Infrastructure Savings: ${get_total_savings()}")
print(f"✅ Successful Interventions: 1")
print(f"🛠️ Latest Action: ccb66c94 (RESTART_DOCKER)")
print(f"---------------------------------------")
