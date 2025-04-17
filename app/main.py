from app.rag.rag_engine import run_rag_pipeline
from app.rag.acadza_concept_tree import load_concept_tree
from app.modules.builders import build_payload
from app.rag.param_config import get_param_specs
from app.modules.utils import get_concepts, get_subconcepts
from app.modules.logger import (
    log_sent_chunks,
    log_gpt_response,
    log_enriched_portion,
    log_builder_call,
    log_final_payload
)
import json

# -----------------------------
# 🚀 Main Orchestrator
# -----------------------------
def run_orchestrator(query, student_id=None):
    #acadza_tree = load_concept_tree()
    final_payloads = []
    combined_tasks = {}
    counter_map = {
        "practiceAssignment": 0,
        "practiceTest": 0,
        "formula": 0,
        "revision": 0,
        "concept": 0,
        "clickingPower": 0,
        "pickingPower": 0,
        "speedRace": 0
    }

    # 🔍 Step 1: Run RAG Pipeline
    result = run_rag_pipeline(query)
    chunks = result.get("chunks", [])
    request_list = result.get("requestList", [])
    analyze_text = result.get("reasoning", "")
    response_text = result.get("script", "")

    log_sent_chunks(query, chunks)
    log_gpt_response(query, request_list)

    print("\n🧠 GPT's requestList:")
    print(json.dumps(request_list, indent=2))

    for req in request_list:
        dost_type = req.get("dost_type")
        subject = req.get("subject")

        if not subject or not dost_type:
            print(f"❌ Missing subject or dost_type in request: {req}")
            continue

        param_specs = get_param_specs(dost_type)
        expected = param_specs.get("expected_fields", [])
        defaults = param_specs.get("defaults", {})

        for field in expected:
            if field not in req:
                req[field] = defaults.get(field)

        chapter_groups = req.get("chapter_groups", [])
        if not chapter_groups:
            print(f"❌ Missing chapter_groups in request: {req}")
            continue

        enriched_groups = []
        for group in chapter_groups:
            chapter = group.get("chapter")
            subject = group.get("subject")

            concepts = group.get("concepts") or get_concepts(subject, chapter)
            subconcepts = group.get("subconcepts") or {
                c: get_subconcepts(subject, chapter, c) for c in concepts
            }

            enriched_groups.append({
                "subject": subject,
                "chapter": chapter,
                "concepts": concepts,
                "subconcepts": subconcepts
            })

        log_enriched_portion(dost_type, enriched_groups)

        counter = counter_map[dost_type]
        key = (dost_type, subject, counter)

        if key not in combined_tasks:
            combined_tasks[key] = req.copy()

        combined_tasks[key]["chapter_groups"] = combined_tasks[key].get("chapter_groups", []) + enriched_groups
        counter_map[dost_type] += 1

    for key, task in combined_tasks.items():
        dost_type, subject = task["dost_type"], task["subject"]
        print(f"\n⚙️ Building payload for DOST: {dost_type} | Subject: {subject}")
        log_builder_call(dost_type, subject, task)

        payload = build_payload(dost_type, task, student_id)

        if student_id and not any(k in payload and payload[k] == student_id for k in ["userId", "studentid", "user"]):
            print(f"⚠️ Student ID was not correctly injected in builder for {dost_type}")

        if payload:
            final_payloads.append(payload)
            print("✅ Payload built successfully!")
        else:
            print(f"❌ Payload generation failed for {dost_type} → {subject}")
            print(f"🔍 Debug Task Data: {json.dumps(task, indent=2)}")

    if not final_payloads:
        print("❌ No valid payloads generated for this query. Possible issue in GPT extraction or chapter mismatch.")

    log_final_payload(query, final_payloads)

    return {
        "raw_query": query,
        "requestList": final_payloads,
        "queryAnalyzeText": analyze_text,  # ✅ Backend-only reasoning
        "queryResponseText": response_text  # ✅ Friendly frontend script
    }

# -----------------------------
# 🧪 Manual CLI Runner
# -----------------------------
if __name__ == "__main__":
    query = input("\n🎤 Enter student query: ")
    output = run_orchestrator(query)
    print("\n✅ Final API Payload:\nExecution Finished!")
    print(json.dumps(output, indent=2))
