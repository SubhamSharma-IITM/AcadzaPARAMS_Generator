# 📦 retriever.py — Optimized: First 7 Unique Chapters with Top-1 Chunks

import os
import json
import faiss
import numpy as np
import tiktoken
from tqdm import tqdm
from openai import OpenAI



# 🔑 Configs
INDEX_PATH = "app/rag/faiss_index.idx"
CHUNKS_PATH = "app/rag/chunk_data.json"
VECTORS_PATH = "app/rag/embedding_vectors.npy"
EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_CUTOFF = 0.50
MAX_CHAPTERS = 21

openai = OpenAI()
encoding = tiktoken.encoding_for_model("gpt-4o")

# -----------------------------
# 📥 Load Vector Index
# -----------------------------
def load_faiss_index():
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError("❌ FAISS index not found. Please run build_index.py first.")

    index = faiss.read_index(INDEX_PATH)
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    vectors = np.load(VECTORS_PATH)
    return index, vectors, chunks

# -----------------------------
# ✅ Embed Query
# -----------------------------
def get_embedding(text):
    response = openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return np.array(response.data[0].embedding).astype("float32")

# -----------------------------
# 🔍 Retrieve Chunks
# -----------------------------
def retrieve_relevant_chunks(query, cutoff=SIMILARITY_CUTOFF):
    print(f"\n🎤 Student Query: {query}")
    query_vector = get_embedding(query)
    index, vectors, chunk_data = load_faiss_index()

    print("🔍 Searching top 100 chunks...")
    scores, indices = index.search(np.array([query_vector]), 100)

    all_filtered = []
    for idx, score in zip(indices[0], scores[0]):
        if idx >= len(chunk_data):
            continue
        if score >= cutoff:
            all_filtered.append(chunk_data[idx])

    if not all_filtered:
        print("❌ No chunks passed cutoff.")
        return []

    print(f"✅ {len(all_filtered)} chunks passed similarity cutoff {cutoff}")

    selected_chunks = []
    from collections import defaultdict

    chapter_chunks = defaultdict(list)

    for chunk in all_filtered:
        chapter_key = f"{chunk.get('subject')}::{chunk.get('chapter')}"
        chapter_chunks[chapter_key].append(chunk)

    for chapter_key, chunks in chapter_chunks.items():
        top_chunks = chunks[:5]  # Pick top 3
        selected_chunks.extend(top_chunks)
        if len(selected_chunks) >= 51:
            selected_chunks = selected_chunks[:51]
            break

    print(f"\n🎯 Retrieved Chunks: {len(selected_chunks)} (Max 3 per chapter, Max 51 overall)")
    for c in selected_chunks:
        print(f"- {c['text']}")

    return selected_chunks


# -----------------------------
# 🧪 Demo
# -----------------------------
if __name__ == "__main__":
    queries = [
       "I’m a student, and I don’t remember the formulas of differential equations. My test is coming up in three or four days, so I need to revise it too. Can you help me out with that?"
    ]

    for i, q in enumerate(queries, 1):
        print(f"\n==================== QUERY {i} ====================")
        _ = retrieve_relevant_chunks(q)
