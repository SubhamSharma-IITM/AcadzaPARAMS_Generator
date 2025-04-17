from utils import correct_subject, get_concepts, get_subconcepts
from acadza_concept_tree import load_concept_tree
from difflib import get_close_matches
import tiktoken
from openai import OpenAI
import json

# ========== PART 1: GPT Validator ==========
def gpt_validate_portion(group: dict) -> dict:
    openai = OpenAI()
    encoding = tiktoken.encoding_for_model("gpt-4o")
    query_json = json.dumps(group)

    prompt = f"""
You are a content validation engine for a student AI assistant.

You are given a portion group that includes subject, chapter, concept, and subconcept as extracted from the student's query.

🌟 Your job:
1. Validate whether this combination actually refers to a real academic portion (according to general academic knowledge).
2. If valid, return `portion_valid: true` and echo the cleaned group.
3. If not valid (hallucinated chapter, mismatched concept etc.), return `portion_valid: false`.

📃 Structure to follow:
```json
{{
  "portion_valid": true,
  "validated_groups": [
    {{
      "subject": "...",
      "chapter": "...",
      "concepts": [...],
      "subconcepts": {{
        "Concept1": ["sub1", "sub2"]
      }}
    }}
  ]
}}
```

Student Portion:
```json
{query_json}
```
"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    content = response.choices[0].message.content.strip()
    if "```json" in content:
        content = content.split("```json")[-1].split("```")[0].strip()

    try:
        return json.loads(content)
    except Exception as e:
        return {
            "portion_valid": False,
            "error": str(e),
            "raw_output": content
        }

# ========== PART 2: Retry & Tree Recovery ==========
def fuzzy_retry_for_chapters(group, acadza_tree):
    chapter = (group.get("chapters") or [None])[0]
    subject_hint = group.get("subject", "")
    concepts = group.get("concepts", [])
    subconcepts = group.get("subconcepts", [])

    best_match = None

    # Try cutoff=0.7
    for stream in acadza_tree:
        for subject in acadza_tree[stream]:
            chapters = list(acadza_tree[stream][subject].keys())
            match = get_close_matches(chapter, chapters, n=1, cutoff=0.7)
            if match:
                best_match = (stream, subject, match[0])
                break
        if best_match:
            break

    # Retry with cutoff=0.5
    if not best_match:
        for stream in acadza_tree:
            for subject in acadza_tree[stream]:
                chapters = list(acadza_tree[stream][subject].keys())
                match = get_close_matches(chapter, chapters, n=1, cutoff=0.5)
                if match:
                    best_match = (stream, subject, match[0])
                    break
            if best_match:
                break

    if not best_match:
        return []

    stream, subject, matched_chapter = best_match

    concepts_final = []
    subconcepts_map = {}

    if concepts:
        for concept in concepts:
            tree_concepts = acadza_tree[stream][subject][matched_chapter].keys()
            matched_concept = get_close_matches(concept, tree_concepts, n=1, cutoff=0.6)
            if matched_concept:
                concept_name = matched_concept[0]
                concepts_final.append(concept_name)
                subconcepts_map[concept_name] = list(acadza_tree[stream][subject][matched_chapter][concept_name].keys())
    else:
        concepts_final = list(acadza_tree[stream][subject][matched_chapter].keys())
        for concept_name in concepts_final:
            subconcepts_map[concept_name] = list(acadza_tree[stream][subject][matched_chapter][concept_name].keys())

    return [{
        "subject": subject,
        "chapter": matched_chapter,
        "concepts": concepts_final,
        "subconcepts": subconcepts_map
    }]

# ========== PART 3: Final Wrapper ==========
def validate_portion(group):
    acadza_tree = load_concept_tree()

    gpt_result = gpt_validate_portion(group)

    if not gpt_result.get("portion_valid"):
        return {
            "portion_valid": False,
            "chapter_groups": [],
            "reason": "GPT validation failed"
        }

    validated_groups = gpt_result.get("validated_groups", [])

    final_groups = []
    for vgroup in validated_groups:
        recovered = fuzzy_retry_for_chapters(vgroup, acadza_tree)
        if recovered:
            final_groups.extend(recovered)

    return {
        "portion_valid": bool(final_groups),
        "chapter_groups": final_groups
    }
