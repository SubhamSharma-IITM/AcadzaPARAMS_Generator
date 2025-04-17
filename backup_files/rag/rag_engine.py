from rag.retriever import retrieve_relevant_chunks
from rag.rag_gpt_prompt import get_final_payload_from_gpt

# -----------------------------
# 🎯 RAG Pipeline Entry Point
# -----------------------------
def run_rag_pipeline(query: str) -> dict:
    print(f"\n🚀 RAG PIPELINE STARTED for: '{query}'")

    chunks = retrieve_relevant_chunks(query)
    print(f"🔗 Retrieved {len(chunks)} relevant chunks.")

    result = get_final_payload_from_gpt(query, chunks)
    print("✅ GPT Response Processed.")

    # ✅ Include chunks in the returned result
    return {
        "chunks": chunks,
        "requestList": result.get("requestList", []),
        "reasoning": result.get("reasoning", ""),
        "script": result.get("script", ""),
        "raw_gpt_output": result.get("raw_gpt_output", {})
    }

