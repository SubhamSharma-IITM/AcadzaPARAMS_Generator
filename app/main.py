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
    main_script = result.get("main_script", "")  # ✅ New
    dost_steps = result.get("dost_steps", [])      # ✅ New

    log_sent_chunks(query, chunks)
    log_gpt_response(query, request_list)

    print("\n🧐 GPT's requestList:")
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

        # 🚀 ADD THIS CHECK:
        if dost_type in ["clickingPower", "pickingPower", "speedRace"]:
            enriched_groups = chapter_groups
        else:
            for group in chapter_groups:
                chapter = group.get("chapter")
                subject = group.get("subject")

                if "concepts" not in group:
                    concepts = get_concepts(subject, chapter)
                    subconcepts = {c: get_subconcepts(subject, chapter, c) for c in concepts}
                else:
                    concepts = group.get("concepts", [])
                    if "subconcepts" not in group:
                        subconcepts = {c: get_subconcepts(subject, chapter, c) for c in concepts}
                    else:
                        subconcepts = group.get("subconcepts", {})

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
        # 🚨 Very important correction:
        combined_tasks[key]["chapter_groups"] = enriched_groups  # NOT += anymore
        counter_map[dost_type] += 1

    for key, task in combined_tasks.items():
        dost_type, subject = task["dost_type"], task["subject"]
        print(f"\n⚙️ Building payload for DOST: {dost_type} | Subject: {subject}")
        log_builder_call(dost_type, subject, task)

       

        payload = build_payload(dost_type, task, student_id)

        if student_id and not any(k in payload and payload[k] == student_id for k in ["userId", "studentid", "user"]):
            print(f"⚠️ Student ID was not correctly injected in builder for {dost_type}")

        if payload:
            if isinstance(payload, list):
                final_payloads.extend(payload)
            else:
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
        "queryAnalyzeText": analyze_text,   # 🔍 For backend logging
        "main_script": main_script,         # 🔍 New for frontend motivational journey
        "dost_steps": dost_steps            # 🔍 New for frontend per-DOST scripts
    }

# -----------------------------
# 🧪 Manual CLI Runner
# -----------------------------
if __name__ == "__main__":
    # Simulate a user query manually
    query = "Create a 4-day revision plan for Current Electricity. I can give 2 hours per day. And I want to first increase my clicking power and then race with air 1 on this topic. I am slow in it please help."

    # Dummy student_id for testing
    student_id = "test_student_123"

    print("\n🚀 Starting manual dry run for run_orchestrator()...\n")

    result = run_orchestrator(query, student_id=student_id)

    print("\n✅ FINAL OUTPUT from run_orchestrator():")
    import json
    print(json.dumps(result, indent=2))

