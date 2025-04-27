from app.rag.retriever import retrieve_relevant_chunks
from app.rag.rag_gpt_prompt import get_final_payload_from_gpt

# -----------------------------
# 🌟 RAG Pipeline Entry Point
# -----------------------------
def run_rag_pipeline(query: str) -> dict:
    print(f"\n🚀 RAG PIPELINE STARTED for: '{query}'")

    chunks = retrieve_relevant_chunks(query)
    print(f"🔗 Retrieved {len(chunks)} relevant chunks.")

    result = get_final_payload_from_gpt(query, chunks)
    print("✅ GPT Response Processed.")
    test_dost=result.get("dost_steps",[])
    print(test_dost)
    # ✅ Include chunks in the returned result
    return {
        "chunks": chunks,
        "requestList": result.get("requestList", []),
        "reasoning": result.get("reasoning", ""),
        "main_script": result.get("main_script", ""),
        "dost_steps": result.get("dost_steps", []),
        "raw_gpt_output": result.get("raw_gpt_output", {})
    }

# -----------------------------
# �\udeaa Manual CLI Runner
# -----------------------------
if __name__ == "__main__":
    predefined_queries = [
        "Make an assignment from Gravitation (moderate level), test from Thermodynamics (easy level), and a concept basket from SHM."
    ]

    for i, query in enumerate(predefined_queries, 1):
        print(f"==================== QUERY {i} ====================")
        payload = run_rag_pipeline(query)

        import json
        print("\n\u2705 Final RAG Payload:")
        print(json.dumps(payload, indent=2))
