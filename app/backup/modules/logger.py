# 📜 logger.py — Clean and Optimized Logging System
import os
import json
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "query_log.txt")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# -----------------------------
# ✅ Log Single Phase Output (Optional Utility)
# -----------------------------
def log_phase_output(phase_name: str, content: dict):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_block = {
        "timestamp": timestamp,
        "phase": phase_name,
        "output": content
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + json.dumps(log_block, indent=2) + "\n")

# -----------------------------
# ✅ Save Full Orchestrator Log
# -----------------------------
def save_full_log(query: str, logs: dict, final_output: dict = None, errors: list = None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_log = {
        "timestamp": timestamp,
        "query": query,
        "phases": logs,
        "final_output": final_output if final_output else [],
        "errors": errors if errors else []
    }
    "retrieved_chunks": [c['text'] for c in chunks] 
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n===== QUERY EXECUTION =====\n")
        f.write(json.dumps(full_log, indent=2) + "\n")
