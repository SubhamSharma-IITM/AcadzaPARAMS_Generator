# 🛠️ utils.py — Cleaned and Finalized for RAG Pipeline with Fallbacks & Logs
import sys
import os
import tiktoken
from difflib import get_close_matches
from app.modules.acadza_concept_tree import load_concept_tree

# 🔁 Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load once
acadza_tree = load_concept_tree()
encoding = tiktoken.encoding_for_model("gpt-4o")

# -----------------------------
# ✅ Token Counting
# -----------------------------
def count_tokens(text):
    return len(encoding.encode(text))

# -----------------------------
# ✅ Subject Corrector (with Fallback Logging)
# -----------------------------
def correct_subject(chapter, subject_hint):
    for stream in acadza_tree:
        for subject in acadza_tree[stream]:
            chapters = list(acadza_tree[stream][subject].keys())
            match = get_close_matches(chapter, chapters, n=1, cutoff=0.7)
            if match:
                print(f"✅ Subject correction: '{chapter}' found under subject '{subject}'")
                return subject
    print(f"⚠️ Subject correction failed for chapter '{chapter}', using hint '{subject_hint}'")
    return subject_hint

# -----------------------------
# ✅ Concept + Subconcept Fetchers (with Stream Search)
# -----------------------------
def get_concepts(subject: str, chapter: str) -> list:
    for stream in acadza_tree:
        if subject in acadza_tree[stream] and chapter in acadza_tree[stream][subject]:
            return list(acadza_tree[stream][subject][chapter].keys())
    print(f"⚠️ get_concepts(): Chapter '{chapter}' not found under subject '{subject}'")
    return []

def get_subconcepts(subject: str, chapter: str, concept: str) -> list:
    for stream in acadza_tree:
        if concept in acadza_tree[stream].get(subject, {}).get(chapter, {}):
            return acadza_tree[stream][subject][chapter][concept]
    print(f"⚠️ get_subconcepts(): Subconcepts not found for {subject} > {chapter} > {concept}")
    return []

# -----------------------------
# ✅ Validators with Logs
# -----------------------------
def is_valid_chapter(subject: str, chapter: str) -> bool:
    for stream in acadza_tree:
        if subject in acadza_tree[stream] and chapter in acadza_tree[stream][subject]:
            return True
    print(f"❌ Invalid Chapter: {chapter} under {subject}")
    return False

def is_valid_concept(subject: str, chapter: str, concept: str) -> bool:
    for stream in acadza_tree:
        if concept in acadza_tree[stream].get(subject, {}).get(chapter, {}):
            return True
    print(f"❌ Invalid Concept: {concept} under {subject} > {chapter}")
    return False

def is_valid_subconcept(subject: str, chapter: str, concept: str, subconcept: str) -> bool:
    for stream in acadza_tree:
        if subconcept in acadza_tree[stream].get(subject, {}).get(chapter, {}).get(concept, []):
            return True
    print(f"❌ Invalid Subconcept: {subconcept} under {subject} > {chapter} > {concept}")
    return False

# -----------------------------
# ✅ Practice Portion Builder with Logs
# -----------------------------
def build_practice_portion(chapter_groups):
    portion = []
    print("\n📦 Building practicePortion:")
    for group in chapter_groups:
        subject = group.get("subject")
        chapter = group.get("chapter")
        if not subject or not chapter:
            print(f"❌ Skipping group: Missing subject or chapter → {group}")
            continue

        if not is_valid_chapter(subject, chapter):
            subject = correct_subject(chapter, subject)
            if not is_valid_chapter(subject, chapter):
                print(f"❌ Still invalid after correction → {subject} > {chapter}, skipping")
                continue

        concepts = group.get("concepts", [])
        subconcepts_map = group.get("subconcepts", {})

        print(f"📘 {subject} > {chapter}")
        for concept in concepts:
            if not is_valid_concept(subject, chapter, concept):
                continue

            subconcepts = subconcepts_map.get(concept, [])
            if subconcepts:
                for sub in subconcepts:
                    if not is_valid_subconcept(subject, chapter, concept, sub):
                        continue
                    portion.append({
                        "id": "",
                        "content": {
                            "subject": subject,
                            "chapter": chapter,
                            "concept": concept,
                            "subConcept": sub
                        }
                    })
                    print(f"   ➕ {concept} → {sub}")
            else:
                portion.append({
                    "id": "",
                    "content": {
                        "subject": subject,
                        "chapter": chapter,
                        "concept": concept
                    }
                })
                print(f"   ➕ {concept} → [no subconcepts]")

    if not portion:
        print("⚠️ No valid practicePortion built for provided chapter_groups")

    return portion
