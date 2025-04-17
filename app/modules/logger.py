# 📜 logger.py — Sherlock-Style Full Execution Logging

import os
import json
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "query_log.txt")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# -----------------------------
# ✅ Basic Utilities
# -----------------------------
def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------
# ✅ Log: GPT Chunks Sent
# -----------------------------
def log_sent_chunks(query, chunks):
    log_block = {
        "timestamp": _timestamp(),
        "step": "Chunks Sent to GPT",
        "query": query,
        "chunk_count": len(chunks),
        "chunk_sample": [c.get("text") for c in chunks[:5]]
    }
    _write_log_block(log_block)

# -----------------------------
# ✅ Log: GPT Response
# -----------------------------
def log_gpt_response(query, request_list):
    log_block = {
        "timestamp": _timestamp(),
        "step": "GPT Response (requestList)",
        "query": query,
        "requestList": request_list
    }
    _write_log_block(log_block)

# -----------------------------
# ✅ Log: Enriched Portions from Main
# -----------------------------
def log_enriched_portion(dost_type, enriched_groups):
    log_block = {
        "timestamp": _timestamp(),
        "step": f"Enriched Portion for {dost_type}",
        "portion": enriched_groups
    }
    _write_log_block(log_block)

# -----------------------------
# ✅ Log: Builder Invocation
# -----------------------------
def log_builder_call(dost_type, subject, portion):
    log_block = {
        "timestamp": _timestamp(),
        "step": f"Builder Called: {dost_type} | Subject: {subject}",
        "portion": portion
    }
    _write_log_block(log_block)

# -----------------------------
# ✅ Log: Final API Payload
# -----------------------------
def log_final_payload(query, final_payloads):
    log_block = {
        "timestamp": _timestamp(),
        "step": "Final API Payload",
        "query": query,
        "requestList": final_payloads
    }
    _write_log_block(log_block)

# -----------------------------
# 🔐 Internal Write Function
# -----------------------------
def _write_log_block(block):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n===== LOG ENTRY =====\n")
        f.write(json.dumps(block, indent=2) + "\n")
