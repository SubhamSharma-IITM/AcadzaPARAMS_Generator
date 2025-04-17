import json
from openai import OpenAI
import tiktoken
from typing import List, Dict

# -----------------------------
# 🔑 OpenAI Setup
# -----------------------------
openai = OpenAI()
encoding = tiktoken.encoding_for_model("gpt-4o")

# -----------------------------
# 🧐 Construct GPT Prompt from Chunks
# -----------------------------
def generate_rag_prompt(query: str, chunks: List[Dict]) -> str:
    from param_config import allowed_dosts, get_param_specs

    chunk_texts = [f"- {c['text']}" for c in chunks]
    chunk_context = "\n".join(chunk_texts)

    # Step 1: Format allowed DOST types
    dost_types_text = "\n".join([
        f"- {parent} → {subdosts}" for parent, subdosts in allowed_dosts.items()
    ])

    # Step 2: Generate parameter field rules for each DOST
    param_rules = []
    for subdost in [sd for group in allowed_dosts.values() for sd in group]:
        specs = get_param_specs(subdost)
        expected = specs.get("expected_fields", [])
        defaults = specs.get("defaults", {})
        rule = f"{subdost} → expected_fields: {expected} | defaults: {defaults}"
        param_rules.append(rule)

    param_rules_text = "\n".join(param_rules)

    prompt = f"""
PHASE RAG GPT PROMPT (DOST + Portion Extractor)

You are a highly intelligent academic backend agent.
Your job is to analyze a student's query and retrieved academic content (chunks from a tree) and generate structured JSON for downstream payload generation.

🧠 YOUR TASKS:
1. Identify the DOSTs (learning tasks) the student is asking for.
   Allowed DOST types:
{dost_types_text}

2. Based on the query and retrieved chunks, generate a `requestList[]` that:
   - Uses the retrieved portions where possible (DO NOT invent or rephrase chapter/concept names)
   - Uses correct field names per DOST (see rules below)
   - Applies query-extracted values (e.g. difficulty, question count, time)
   - If values are missing, apply DEFAULTS

3. Decide how many DOSTs to generate:
   - If the query clearly requests **one combined DOST** from multiple chapters, concepts or subjects, group them into a single entry.
   - If the query mentions **distinct tasks**, e.g., "one test from ellipse and another from friction", return **two separate DOST entries**.
   - You are allowed to return multiple entries of the **same dost_type** if the portions or intent are different.

4. If the query includes multiple subjects in `chapter_groups[]` and the student intent is ambiguous, set:
   - `subject`: "Mixed"

5. You MUST include two top-level fields inside the JSON:
- \"reasoning\": (backend-only) strict and professional diagnostic summary
- \"script\": (frontend) warm, encouraging motivational explanation


6. For revision DOST:
  - strategy: Default is 1 unless student specifies a strategy
  - importance: A mapping of concept to "high", "medium", or "low" importance based on tone, urgency, or difficulty in the query
  - daywiseTimePerPortion: time the student can give per day in minutes. If you find that in hours in the query, convert into minutes and send (example: "I can study everyday for 4 hours", then convert 4 hours=240 minutes and so on). **Only return the exact minutes. Do ceiling or floor if necessary but do not return 240.3. Return exact 240**. Return the default value 60 if none found in query)

7. For Concept DOST:
- If the student asks for a “concept basket” (single), then group all relevant chapters and concepts into a single DOST.
- Only return multiple DOSTs if the student very clearly asks for separate baskets (e.g., “two different concept baskets”).
- Merge all chapters into a single `chapter_groups` list.
- Do not split them just because the chapters are different.
  
📦 FIELD RULES:
{param_rules_text}

❌ DO NOT invent fields like "examType", "ncertRef", "reason", etc.
👌 DO NOT rephrase chapter/concept/subconcept names.
🔓 You MUST use the 'text' field from each chunk to infer valid portion structure.

🔹 VERY IMPORTANT:
- If the student query asks for a **full chapter** or **only mentions chapter names** without specific concepts, then:
  - Return ONLY the subject and chapter in `chapter_groups[]`
- DO NOT fill concepts/subconcepts in that case (leave them empty)
- DO NOT rephrase any names (subject/chapter/concept/subconcept)
- You MUST copy-paste them exactly as in chunks.
- Match punctuation, spaces, and case **precisely**.
- You MUST include a top-level `subject` field in each DOST entry.
- If you see the abbreviation of a Portion(Chapter/Concept/Subconcept) from the chunk context in the query like NLM for Newton's law of motion or SHM for Simple harmonic motion or Oscillations (SHM) and so on for other words then use that exact word from the chunk in the response list.

Examples:
- ✅ Full chapter query:
```json
"chapter_groups": [
  {{"subject": "Physics", "chapter": "Simple Harmonic Motion"}}
]
```

- ✅ Concept-level query:
```json
"chapter_groups": [
  {{
    "subject": "Physics",
    "chapter": "Newton's law of motion",
    "concepts": ["Pseudo force"]
  }}
]
```

- ✅ Multiple DOSTs of same type:
```json
"requestList": [
  {{
    "dost_type": "practiceTest",
    "subject": "Physics",
    "chapter_groups": [{{"subject": "Physics", "chapter": "Work, power and energy"}}]
  }},
  {{
    "dost_type": "practiceTest",
    "subject": "Physics",
    "chapter_groups": [{{"subject": "Physics", "chapter": "Oscillations (SHM)"}}]
  }}
]
```

=== STUDENT QUERY (DO NOT ASK FOR IT AGAIN) ===
Query: "{query}"

=== RETRIEVED CHUNKS FROM TREE ===
{chunk_context}

🌟 FINAL GOAL:
Return ONLY the following JSON format:
```json
{{
  "requestList": [
    {{
      "dost_type": "practiceAssignment",
      "subject": "Physics",
      "chapter_groups": [
        {{
          "subject": "Physics",
          "chapter": "Newton's Laws of Motion",
          "concepts": ["Friction"],
          "subconcepts": {{
            "Friction": ["Pseudo Force"]
          }}
        }}
      ],
      "difficulty": "moderate",
      "type_split": {{"scq": 20, "mcq": 10}}
    }}
  ],
  "reasoning": "Student asked for detailed assignment and script reasoning. They mentioned confusion in friction, so a moderate assignment was proposed.",
  "script": "I've created a focused assignment on Friction to help you master NLM concepts. Let's crack this together!"
}}

```
You MUST return only this JSON. DO NOT explain anything or apologize.
"""
    return prompt



# -----------------------------
# 🤖 Call GPT to Get Final Payload
# -----------------------------
def get_final_payload_from_gpt(query: str, chunks: List[Dict]) -> dict:
    prompt = generate_rag_prompt(query, chunks)
    input_tokens = len(encoding.encode(prompt))

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    content = response.choices[0].message.content.strip()
    raw_gpt_output = content  # 🧠 Save raw GPT output for logs

    if "```json" in content:
        content = content.split("```json")[-1].split("```")[0].strip()

    try:
        parsed = json.loads(content)
        parsed["_tokens"] = {
            "input": input_tokens,
            "output": len(encoding.encode(content))
        }
        return {
    "requestList": parsed.get("requestList", []),
    "reasoning": parsed.get("reasoning", ""),
    "script": parsed.get("script", ""),         # ✅ MISSING EARLIER
    "raw_gpt_output": raw_gpt_output,
    "_tokens": parsed.get("_tokens", {})
          }


    except Exception as e:
        return {
            "requestList": [],
            "reasoning": None,
            "raw_gpt_output": raw_gpt_output,
            "error": str(e)
        }


# -----------------------------
# 🧪 Demo Runner
# -----------------------------
if __name__ == "__main__":
    from retriever import retrieve_relevant_chunks

    predefined_queries = [
      "Give me one test from kinematics and ellipse"
    ]

    for i, query in enumerate(predefined_queries, 1):
        print(f"==================== QUERY {i} ====================")
        chunks = retrieve_relevant_chunks(query)
        payload = get_final_payload_from_gpt(query, chunks)

        print("✅ Final DOST Payload:")
        print(json.dumps(payload, indent=2))
