# 🎯 phase1.py — DOST + Content Extractor (Phase 1)

import json
import tiktoken
from openai import OpenAI

encoding = tiktoken.encoding_for_model("gpt-4o")
openai = OpenAI()

# -----------------------------
# 🔍 Phase 1: DOST Detection
# -----------------------------

def detect_dost_and_content(query: str) -> dict:
    query_json = json.dumps(query)

    prompt = f"""
    PHASE 1 GPT PROMPT (Detect DOST Type + Chapter + Concept + Subconcept)

    You are an intelligent backend agent for a student query system.
    Your job is to extract the student's intent from their voice/text query and convert it into structured content.

    Your goals:
    1. Identify the DOST type the student is asking for. DOSTs include:
        - Concept Dost → ["concept"]
        - Formula Dost → ["formula"]
        - Revision Dost → ["revision"]
        - Practice Dost → ["practiceAssignment", "practiceTest"]
        - Speed Booster Dost → ["clickingPower", "pickingPower", "speedRace"]

    2. For each DOST task, extract:
        - subject (Physics, Chemistry, Biology, Math)
        - category: "JEE" for Physics, Chemistry, Math; "NEET" for Biology
        - chapter names mentioned
        - concepts (if any mentioned)
        - subconcepts (if any mentioned)

    🧠 Inference Rules:
    - If the query mentions a subconcept or concept but not the chapter, infer the chapter name based on domain knowledge.
    - If only a chapter is mentioned, assume the student wants the full chapter.
    - If both concept and subconcept are given, preserve both.

    🎯 Response Format:
    ```json
    {{
      "tone": "motivated",
      "detected_groups": [
        {{
          "dost_type": "practiceAssignment",
          "category": "JEE",
          "subject": "Physics",
          "chapters": ["Newton's Laws of Motion"],
          "concepts": ["Friction"],
          "subconcepts": ["Pseudo force"]
        }}
      ],
      "raw_query": {query_json}
    }}
    
    ✅ Strict Rules:
    - Only return DOST types from the allowed list
    - Do not invent new chapters or concepts
    - Do not return empty JSON or undefined types
    - Maintain valid JSON structure and all required keys
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
        result = json.loads(content)
        result["_tokens"] = {
            "input": input_tokens,
            "output": len(encoding.encode(content))
        }
        return result

    except Exception as e:
        return {"error": str(e), "raw_output": content}
