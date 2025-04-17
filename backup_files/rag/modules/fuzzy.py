# 🔍 fuzzy.py — Context Matcher + Cleaner (Patch 8 Integrated)
import sys
import os

# 🔁 Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.acadza_concept_tree import load_concept_tree
from modules.utils import get_concepts, get_subconcepts
from difflib import get_close_matches

# --------------------------
# ✅ Fuzzy Match Context
# --------------------------
def fuzzy_match_context(acadza_tree: dict, detected_groups: list) -> dict:
    matched_context = {}

    for group in detected_groups:
        chapters = group.get("chapters", [])
        concepts = group.get("concepts", [])
        subconcepts = group.get("subconcepts", [])
        subject_hint = group.get("subject", "")

        # --- Chapter Matching ---
        for chapter in chapters:
            chapter_matched = False
            corrected_subject = subject_hint

            for stream in acadza_tree:
                for subject in acadza_tree[stream]:
                    chapter_list = list(acadza_tree[stream][subject].keys())
                    match = get_close_matches(chapter, chapter_list, n=1, cutoff=0.7)
                    if match:
                        actual_chapter_key = match[0]
                        corrected_subject = subject
                        matched_context.setdefault(corrected_subject, {})
                        matched_context[corrected_subject].setdefault(actual_chapter_key, {
                            "concepts": [],
                            "subconcepts": {}
                        })
                        chapter_matched = True

            # ✅ Patch 8: If chapter not matched, try concept as chapter
            if not chapter_matched:
                for concept_as_chapter in concepts:
                    for stream in acadza_tree:
                        for subject in acadza_tree[stream]:
                            chapter_list = list(acadza_tree[stream][subject].keys())
                            match = get_close_matches(concept_as_chapter, chapter_list, n=1, cutoff=0.7)
                            if match:
                                actual_chapter_key = match[0]
                                matched_context.setdefault(subject, {})
                                matched_context[subject].setdefault(actual_chapter_key, {
                                    "concepts": [], "subconcepts": {}
                                })
                                print(f"🔄 Promoted concept '{concept_as_chapter}' to chapter → {actual_chapter_key}")

        # --- Concept Matching ---
        for concept in concepts:
            for stream in acadza_tree:
                for subject in acadza_tree[stream]:
                    for chapter in acadza_tree[stream][subject]:
                        concept_list = list(acadza_tree[stream][subject][chapter].keys())
                        match = get_close_matches(concept, concept_list, n=1, cutoff=0.7)
                        if match:
                            canonical_concept = match[0]
                            matched_context.setdefault(subject, {})
                            matched_context[subject].setdefault(chapter, {
                                "concepts": [], "subconcepts": {}
                            })
                            if canonical_concept not in matched_context[subject][chapter]["concepts"]:
                                matched_context[subject][chapter]["concepts"].append(canonical_concept)

        # --- Subconcept Matching ---
        for subconcept in subconcepts:
            for stream in acadza_tree:
                for subject in acadza_tree[stream]:
                    for chapter in acadza_tree[stream][subject]:
                        for concept in acadza_tree[stream][subject][chapter]:
                            sub_list = acadza_tree[stream][subject][chapter][concept]
                            match = get_close_matches(subconcept, sub_list, n=1, cutoff=0.7)
                            if match:
                                canonical_sub = match[0]
                                matched_context.setdefault(subject, {})
                                matched_context[subject].setdefault(chapter, {
                                    "concepts": [], "subconcepts": {}
                                })
                                if concept not in matched_context[subject][chapter]["concepts"]:
                                    matched_context[subject][chapter]["concepts"].append(concept)
                                matched_context[subject][chapter]["subconcepts"].setdefault(concept, []).append(canonical_sub)

    return matched_context


# --------------------------
# ✅ Clean Context for Phase 2
# --------------------------
def clean_context_for_phase2(matched_context, acadza_tree):
    cleaned = {}
    for subject, chapters in matched_context.items():
        cleaned[subject] = {}
        for chapter, data in chapters.items():
            concepts = data.get("concepts", [])
            subconcepts = data.get("subconcepts", {})

            if not concepts:
                try:
                    fallback_concepts = get_concepts(subject, chapter)
                    fallback_subconcepts = {
                        concept: get_subconcepts(subject, chapter, concept)
                        for concept in fallback_concepts
                    }
                    cleaned[subject][chapter] = {
                        "concepts": fallback_concepts,
                        "subconcepts": fallback_subconcepts
                    }
                    print(f"🟡 Fallback concepts loaded for {subject} > {chapter}")
                except Exception as e:
                    print(f"❌ Fallback failed for {subject} > {chapter}: {e}")
                    cleaned[subject][chapter] = None

            else:
                partial = {"concepts": [], "subconcepts": {}}
                for concept in concepts:
                    sub_list = subconcepts.get(concept, [])
                    if not sub_list:
                        try:
                            sub_list = get_subconcepts(subject, chapter, concept)
                        except:
                            sub_list = []
                    partial["concepts"].append(concept)
                    partial["subconcepts"][concept] = sub_list
                cleaned[subject][chapter] = partial
    return cleaned
