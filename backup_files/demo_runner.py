# 🧪 demo_runner.py — Manual Testing Tool for QueryDost (RAG Pipeline)

import os
import json
from datetime import datetime
from main import run_orchestrator
from modules.logger import log_final_payload

# -----------------------------
# 🔁 Predefined Test Cases
# -----------------------------
predefined_queries = [
    "Give me one test from kinematics and ellipse",
    "Give me 2 formula sheets from ellipse and kinematics",
    "One assignment from Plant Kingdom",
    "One revision plan from Thermodynamics",
    "Give me 2 tests: one from SHM+Biomolecules, another from NLM"
]

# -----------------------------
# 💾 Save Payloads for Postman/API
# -----------------------------
def save_payload_to_file(query, payload):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = query[:40].replace(" ", "_").replace("/", "_").replace("?", "")
    filename = f"payloads/output_{safe_name}_{timestamp}.json"
    os.makedirs("payloads", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"📁 Payload saved to: {filename}")

# -----------------------------
# 🧠 Manual or Batch Mode
# -----------------------------
def run_demo():
    print("\n🔍 Welcome to QueryDost Demo Runner")
    print("1. Run custom query")
    print("2. Run all predefined queries")

    choice = input("\nSelect an option [1/2]: ").strip()

    if choice == "1":
        query = input("\n🎤 Enter your test query: ")
        result = run_orchestrator(query)
        print("\n✅ Final Output:")
        print(json.dumps(result, indent=2))
        if not result.get("requestList"):
            print("⚠️  WARNING: No DOSTs generated for this query.")
        save_payload_to_file(query, result)
        log_final_payload(query, result)

    elif choice == "2":
        for i, q in enumerate(predefined_queries):
            print(f"\n🧪 Running test case {i+1}: {q}")
            result = run_orchestrator(q)
            print("\n📦 Payload:")
            print(json.dumps(result, indent=2))
            if not result.get("requestList"):
                print("⚠️  WARNING: No DOSTs generated for this query.")
            save_payload_to_file(q, result)
            log_final_payload(q, result)
            print("\n" + "="*60)

    else:
        print("❌ Invalid option. Exiting.")

# -----------------------------
# 🚀 Run from Terminal
# -----------------------------
if __name__ == "__main__":
    run_demo()
