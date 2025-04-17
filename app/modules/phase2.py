# 🤖 phase2.py — GPT Phase 2: Context Validator + Parameter Extractor (Leak-proof Patch + Patch 7)

import json
import tiktoken
from openai import OpenAI
from config.param_config import get_param_specs
import sys
import os

# 🔁 Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

encoding = tiktoken.encoding_for_model("gpt-4o")
openai = OpenAI()

# ----------------------------
# 🎯 Phase 2 Main Function
# ----------------------------

def generate_dost_payload(query: str, cleaned_context: dict, param_specs: dict, dost_type: str, retry_count=0, max_retries=2) -> dict:
    # ✅ PATCH 7: Generate a minimal context for GPT prompt (chapter-level only)
    minimal_context = {}
    for subject, chapters in cleaned_context.items():
        minimal_context[subject] = []
        for chapter, content in chapters.items():
            if not content or not content.get("concepts"):
                minimal_context[subject].append(chapter)
            else:
                mini = {"name": chapter}
                if content.get("concepts"):
                    mini["concepts"] = content["concepts"]
                if content.get("subconcepts"):
                    mini["subconcepts"] = content["subconcepts"]
                minimal_context[subject].append(mini)

    chapter_context_str = json.dumps(minimal_context, indent=2)
    safe_query = json.dumps(query)
    expected_fields = json.dumps(param_specs.get("expected_fields", []), indent=2)
    default_fields = json.dumps(param_specs.get("defaults", {}), indent=2)

    prompt = f"""
    PHASE 2 GPT PROMPT (Strict Mode for DOST → {dost_type})

    You are an expert backend agent for a learning assistant platform.
    You must return a STRICT and FIXED JSON format. No explanations, no deviations.

    🧩 INPUTS:
    1. User Query:
    {safe_query}

    2. Cleaned Academic Context:
    {chapter_context_str}

    🎯 GOAL:
    1. Check if the cleaned_context is a valid match for the query.
    2. If YES → extract DOST-specific parameter(s) using the correct field names only.
    3. If NO → return context_correct = false and corrected_groups[] to retry fuzzy match.

    📦 EXPECTED FIELDS:
    {expected_fields}

    🔐 DEFAULT FIELDS TO USE IF MISSING:
    {default_fields}

    ✅ OUTPUT FORMAT RULES (MANDATORY):
    - Must include: context_correct (bool), requestList (list), correct_content (list of subject → chapter → concepts → subconcepts)
    - Must return ALL requested chapters, concepts, and subconcepts clearly
    - Must include empty arrays if not mentioned (do NOT skip keys)
    - Must respond ONLY in the format shown below — do not add any explanations or stray keys

    🧾 IF CONTEXT IS VALID:
    ```json
    {{
      "context_correct": true,
      "correct_content": [
        {{
          "subject": "Physics",
          "chapter": "Newton's Laws of Motion",
          "concepts": ["Friction"],
          "subconcepts": {{
            "Friction": ["Pseudo force"]
          }}
        }}
      ],
      "requestList": [
        {{
          "subject": "Physics",
          "chapter": "Newton's Laws of Motion",
          "concepts": ["Friction"],
          "subconcepts": {{
            "Friction": ["Pseudo force"]
          }},
          "difficulty": "hard",
          "duration_minutes": 45
        }}
      ]
    }}
    ```

    🧾 IF CONTEXT IS INCORRECT:
    ```json
    {{
      "context_correct": false,
      "rerun_fuzzy": true,
      "corrected_groups": [
        {{
          "dost_type": "{dost_type}",
          "subject": "Physics",
          "chapters": ["Newton's Laws of Motion"]
        }}
      ]
    }}
    ```
    """

    input_tokens = len(encoding.encode(prompt))

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    content = response.choices[0].message.content.strip()
    if "```json" in content:
        content = content.split("```json")[-1].split("```")[-2].strip()

    try:
        content = content.replace("\\\\", "\\\\\\\\")  # escape for LaTeX \\
        result = json.loads(content)
        result["_tokens"] = {
            "input": input_tokens,
            "output": len(encoding.encode(content))
        }

        if not isinstance(result.get("context_correct"), bool):
            raise ValueError("GPT response missing 'context_correct' as boolean")

        # ✅ PATCH 5: Force retry if cleaned_context is empty, even if GPT says 'true'
        def is_cleaned_context_invalid(cleaned):
            if not cleaned:
                return True
            for chapters in cleaned.values():
                if not chapters:
                    return True
                for ch_data in chapters.values():
                    if ch_data is None or not ch_data.get("concepts"):
                        return True
            return False

        if result.get("context_correct") is True and is_cleaned_context_invalid(cleaned_context):
            print("🔁 GPT gave green flag but cleaned_context is empty/null — forcing retry via fuzzy rerun")
            result["context_correct"] = False
            result["rerun_fuzzy"] = True
            result["corrected_groups"] = [
                {
                    "dost_type": dost_type,
                    "subject": subject,
                    "chapters": list(chapters.keys())
                }
                for subject, chapters in cleaned_context.items()
            ]

        if result.get("context_correct") is False:
            if retry_count >= max_retries:
                return result
            if not result.get("rerun_fuzzy") or not result.get("corrected_groups"):
                raise ValueError("Missing required field 'corrected_groups' for rerun_fuzzy")

            from modules.fuzzy import fuzzy_match_context, clean_context_for_phase2
            from modules.acadza_concept_tree import load_concept_tree

            acadza_tree = load_concept_tree()
            corrected_groups = result["corrected_groups"]

            fuzzy_matched = fuzzy_match_context(acadza_tree, detected_groups=corrected_groups)
            cleaned_retry = clean_context_for_phase2(fuzzy_matched, acadza_tree)

            return generate_dost_payload(
                query=query,
                cleaned_context=cleaned_retry,
                param_specs=param_specs,
                dost_type=dost_type,
                retry_count=retry_count + 1
            )

        return result

    except Exception as e:
        return {"error": str(e), "raw_output": content}
