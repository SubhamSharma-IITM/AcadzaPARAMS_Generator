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
    from app.rag.param_config import allowed_dosts, get_param_specs

    chunk_texts = [f"- {c['text']}" for c in chunks]
    chunk_context = "\n".join(chunk_texts)

    dost_types_text = "\n".join([
        f"- {parent} → {subdosts}" for parent, subdosts in allowed_dosts.items()
    ])

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

You are a highly intelligent academic backend agent specialised in the domain of JEE/NEET and 11th and 12th boards.
Your job is to analyze a student's query and retrieved academic content (chunks from a tree) and generate structured JSON for downstream payload generation.

✨ VERY IMPORTANT:
- NEVER invent chapter names, concept names, or subconcepts.
- ALWAYS use exact names from chunks provided.
- NEVER invent fields like "examType", "ncertRef", "reason", etc.
- See if student query demands ncert based content in dosts by direct or indirect reference then include them in the response as strictly as a boolean: True else stick to their default value of false. If yes then only practiceTest and practiceAssignment take these fields as input.
- Maintain strict JSON structure.
- Match punctuation, spaces, and case precisely.
- If the student query asks for a **full chapter** or **only mentions chapter names** without specific concepts or subconcepts, then:
    - Return ONLY the subject and chapter in `chapter_groups[]`
    - DO NOT fill concepts/subconcepts in that case (leave them empty)
- DO NOT rephrase any names (subject/chapter/concept/subconcept)
- If multiple subjects mentioned ambiguously, subject should be 'Mixed'.
- You MUST include a top-level `subject` field in each DOST entry.
- Handle abbreviations properly and use their full form instead from the chunk data(e.g., SHM for Simple Harmonic Motion).
- Decide how many DOSTs to generate:
   - If the query clearly requests **one combined DOST** from multiple chapters, concepts or subjects, group them into a single entry.
   - If the query mentions **distinct tasks**, e.g., "one test from ellipse and another from friction", return **two separate DOST entries**.
   - You are allowed to return multiple entries of the **same dost_type** if the portions or intent are different.
- If the query asks for a concept or subconcept or multiple concepts or subconcepts that you can identify and is present in the chunk data then put that data in their defined place as stated in the examples below of chapter,concept and subconcept level queries and then include into the final request list.
- If the query seems asking portion till the level of concept and you find multiple concepts aligning or potentially incomplete mentioned subconcepts for those concept(s) in the chunk data then just return the data till the concept and donot fill the subconcept field. 
- Keywords like short notes and summary and similar direct or indirect words are pointers towards the need of formula dost.

✨ ALLOWED DOST TYPES:
{dost_types_text}

✨ FIELD RULES:
{param_rules_text}

✨ STRUCTURE OF CHUNKS DATA:
- subject: Main subject name
- chapter: Name of chapter
- concept: Concept within chapter
- subconcept: Subconcept within concept
- You MUST use the 'text' field from each chunk to infer valid portion structure, the Chunk will have structure as Subject > Chapter > Concept > Subconcept. So if subconcept is found in query then extract it from the subconcept part of chunk and put it under subconcepts under the response list and similarly for concepts and chapters and subjects.
- If the Chunks contain "," dont consider them as two different subconcepts or concepts they are just complte names representing what is present in the data base. Example:  "Math > Circle > Tangent and Normal > Tangent from a point outside the Circle, Equation of pair of tangents", so Tangent from a point outside the Circle, Equation of pair of tangents is one single subconcept and not two different ones.
- Strictly ensure this: If the query seems to demand response till subconcept level but the Chunks have more than one subconcept per concept then donot send the subconcept field. 

✨ EXAMPLES OF CORRECT chapter_groups STRUCTURE:
- Full Chapter Query:
```json
"chapter_groups": [
  {{"subject": "Physics", "chapter": "Simple Harmonic Motion"}}
]
```
- Concept Level Query:
```json
"chapter_groups": [
  {{
    "subject": "Physics",
    "chapter": "Newton's Laws of Motion",
    "concepts": ["Friction"]
  }}
]

```
- subconcept Level Query:
```json
"chapter_groups": [
  {{
    "subject": "Physics",
    "chapter": "Newton's Laws of Motion",
    "concepts": ["Friction"],
    "subconcepts": {{
      "Friction": ["Pseudo Force"]
    }}
  }}
]
```

- Multiple DOSTs of Same Type:
```json
"requestList": [
  {{"dost_type": "practiceTest", "subject": "Physics", "chapter_groups": [{{"subject": "Physics", "chapter": "Work, Power and Energy"}}]}},
  {{"dost_type": "practiceTest", "subject": "Physics", "chapter_groups": [{{"subject": "Physics", "chapter": "Oscillations (SHM)"}}]}}
]
```

✨ YOUR TASKS:
1. Based on the query and retrieved chunks, generate a `requestList[]` that:
   - Uses the retrieved portions where possible (DO NOT invent or rephrase chapter/concept names)
   - Uses correct field names per DOST (see rules below)
   - Applies query-extracted values (e.g. difficulty, question count, time)
   - If values are missing, apply DEFAULTS
2. Do NOT mix different DOST types unless asked.
3. For revision DOST:
  - strategy: Default is 1 unless student specifies a strategy
  - importance: A mapping of concept to "high", "medium", or "low" importance based on tone, urgency, or difficulty in the query
  - daywiseTimePerPortion: time the student can give per day in minutes. If you find that in hours in the query, convert into minutes and send (example: "I can study everyday for 4 hours", then convert 4 hours=240 minutes and so on). **Only return the exact minutes. Do ceiling or floor if necessary but do not return 240.3. Return exact 240**. Return the default value 60 if none found in query)
4. If the student uses words like "chamak nahi raha hai" or any direct and indirect reference to the need of clicking power or picking power then give it to them.
5. Maintain correct grouping.
6. NO extra invented fields.
7. Only copy exact portion names.
8. For concept DOST:
  - If you find the name of the chapter in the query which is present in the chunks then only include the name of the chapter in the chapter groups and donot include concepts or subconcepts as the query needs a full length concept for the chapter.

✨ RETURN FORMAT:
Strict JSON:
```json
{{
  "requestList": [...],
  "reasoning": "Diagnostic in short and precise backend reasoning",
  "main_script": "Overall journey description text",
  "dost_steps": [
    {{
      "dost_type": "practiceTest",
      "script": "Personalized step script explaining this DOST"
    }},
    ...
  ]
}}
```

✨ SPECIAL INSTRUCTION FOR DOST SCRIPTS:
For each DOST's `script`:
- Cheerfully explain what task is given.
- The explanation should seem like an adviced doctored prescription to be coming from an expert teacher in the field of JEE/NEET & 11th and 12th boards knowing exactly what the student needs and all their pain points and confusion points and where can they be stuck and so the journey.
- If the query or part of it seems ambiguous or vague, that the student is facing a problem but is not able to exactly know which dost they need then that particular suggested dost should be properly exaplained like how a doctor suggests a pill to a patient with all the crucial details of what it is,how it will help,how to use,what not to do and best practices.
- How that dost will help the student and how can be make the best use of it and why we thought it shall be helpful.
- Mention parameters extracted from query.
- Clearly Mention all the default parameters used gracefully.
- **IMPORTANT**:While mentioning the parameters and portion(for all Chapters,concepts,subconcepts) in the dost script make sure that all of the parameters are included within bold tags such that the frontend can render them as bold, for example: "...with a duration of <b>60 minutes</b>","We have set the difficulty to <b>easy</b>","<b>Chemical Equilibrium</b>..." and so on for all the dost parameters.
- Encourage tweaks.
- End with smart tips to understand and excel the topic & motivation for exams.



Example:
"Here is your Step 1: A moderate-level Practice Test on Parabola and Ellipse.Since you specified moderate difficulty.I used the question split to 20 SCQs and 10 MCQs. Feel free to tweak!"

Example if confused or ambiguous query:
"Here is your Step 1: Since you said that you are facing problems in understanding this topic I have made a dost just for you with all the defaults included and intent set as to why they should use that dost and how they should undertake it and what best practices to keep and what to avoid"

✨ FINAL GOAL:
- main_script clearly,precisely, in-short describes the entire journey cheerfully like a recommendation from an expert teacher specialised for JEE/NEET and 11th and 12th boards.
- dost_steps array explains each DOST properly like a recommendation from a teacher specialised for JEE/NEET and 11th and 12th boards.
- Maintain order with requestList.
- No extra text. Only strict JSON output.

=== STUDENT QUERY ===
Query: "{query}"

=== RETRIEVED CHUNKS ===
{chunk_context}
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
    raw_gpt_output = content

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
            "main_script": parsed.get("main_script", ""),
            "dost_steps": parsed.get("dost_steps", []),
            "raw_gpt_output": raw_gpt_output,
            "_tokens": parsed.get("_tokens", {})
        }

    except Exception as e:
        return {
            "requestList": [],
            "reasoning": None,
            "main_script": None,
            "dost_steps": [],
            "raw_gpt_output": raw_gpt_output,
            "error": str(e)
        }

# -----------------------------
# 🧪 Demo Runner (Local)
# -----------------------------
if __name__ == "__main__":
    from retriever import retrieve_relevant_chunks

    predefined_queries = [
        "Make an assignment from Gravitation (moderate level), test from Thermodynamics (easy level), and a concept basket from SHM, aur mujhe na NLM chamak nahi raha hai kya karu."
    ]

    for i, query in enumerate(predefined_queries, 1):
        print(f"==================== QUERY {i} ====================")
        chunks = retrieve_relevant_chunks(query)
        payload = get_final_payload_from_gpt(query, chunks)

        print("\n✅ Final DOST Payload:")
        print(json.dumps(payload, indent=2))
