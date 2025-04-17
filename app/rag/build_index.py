import json
import os
from openai import OpenAI
import numpy as np
import faiss
from tqdm import tqdm

# -----------------------------
# 📁 INPUT FILE
# -----------------------------
TREE_PATH = "acadza_concept_tree.json"
CHUNK_OUTPUT_PATH = "rag/chunk_data.json"
EMBEDDING_OUTPUT_PATH = "rag/embedding_vectors.npy"
FAISS_INDEX_PATH = "rag/faiss_index.idx"

# -----------------------------
# 🔑 OpenAI Client Setup
# -----------------------------
openai = OpenAI()

# -----------------------------
# ✅ Helper: Load Concept Tree
# -----------------------------
def load_concept_tree():
    with open(TREE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# -----------------------------
# 📦 Helper: Flatten Tree to Chunks
# -----------------------------
def flatten_tree_to_chunks(tree):
    chunks = []
    for stream in tree:
        for subject in tree[stream]:
            for chapter in tree[stream][subject]:
                for concept in tree[stream][subject][chapter]:
                    subconcepts = tree[stream][subject][chapter][concept]
                    if not subconcepts:
                        chunks.append({
                            "subject": subject,
                            "chapter": chapter,
                            "concept": concept,
                            "subconcept": "",
                            "text": f"{subject} > {chapter} > {concept}"
                        })
                    else:
                        for sub in subconcepts:
                            chunks.append({
                                "subject": subject,
                                "chapter": chapter,
                                "concept": concept,
                                "subconcept": sub,
                                "text": f"{subject} > {chapter} > {concept} > {sub}"
                            })
    return chunks

# -----------------------------
# 🔬 Helper: Embed Chunks
# -----------------------------
def embed_chunks(texts, model="text-embedding-3-small", batch_size=300):
    print("\n🔍 Generating embeddings in batches...")
    all_vectors = []
    for i in tqdm(range(0, len(texts), batch_size)):
        batch = texts[i:i+batch_size]
        response = openai.embeddings.create(
            model=model,
            input=batch
        )
        vectors = [item.embedding for item in response.data]
        all_vectors.extend(vectors)
    return np.array(all_vectors)


# -----------------------------
# 💾 Save FAISS Index
# -----------------------------
def save_faiss_index(vectors):
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, FAISS_INDEX_PATH)
    return index

# -----------------------------
# 🚀 Main Function
# -----------------------------
def create_faiss_index():
    print("\n📥 Loading Concept Tree...")
    tree = load_concept_tree()

    print("\n📦 Flattening into chunks...")
    chunks = flatten_tree_to_chunks(tree)

    print(f"✅ Total Chunks: {len(chunks)}")

    texts = [chunk["text"] for chunk in chunks]
    vectors = embed_chunks(texts)

    print("\n💾 Saving embeddings and chunks...")
    os.makedirs("rag", exist_ok=True)
    with open(CHUNK_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)
    np.save(EMBEDDING_OUTPUT_PATH, vectors)

    print("\n📡 Creating FAISS index...")
    save_faiss_index(vectors)

    print("\n✅ FAISS index created and saved.")

# -----------------------------
# 🧪 Run Directly
# -----------------------------
if __name__ == "__main__":
    create_faiss_index()
