# 📜 query_checker.py — SuperDOST Enhanced Query Classification & Structuring

import json
from typing import Literal
from openai import OpenAI
import re

# Initialize OpenAI client
openai = OpenAI()


def query_checker(
    text: str,
    *,
    translate_if_dost_or_mixed: bool = False,
    input_type: Literal["text", "image"] = "text"
) -> dict:
    """
    Classify student queries into 'dost', 'general', 'mixed', or detect harmful content.
    For 'general' and 'mixed', return a richly structured 'structured_answer' array.
    If translate_if_dost_or_mixed is True and mode is 'dost' or 'mixed', also return 'translated'.
    input_type informs prompt: 'image' input may contain diagrams, LaTeX, labels.
    """

    # System-level instructions
    system_instructions = rf"""
You are ACADZA’s SuperDOST query classifier.

• Input Type: {input_type}
  - If "image", the text may include diagram descriptions (e.g. "circle labeled r=5 cm"), raw labels, and LaTeX equations. Extract **all** details precisely.
  - VERY IMPORTANT:**If Input Type is "image" AND the user’s context (below) contains no explicit request for assignment/test/formula/revision/practice,etc., then you MUST set `"mode":"general"` and skip any DOST logic.**  
  - If the input is an "image" and mode is "mixed" and the query includes vague intent like:
     "Help me solve this and give similar questions to practice/revise/any dost..."
     You MUST enrich the "translated" text by appending a clear intent like:
     “The student wants a [DOST_TYPE] for the [mention the topics or portion]"
     Examples:
     "Help me solve this." →
     "Help me solve this. The student wants a practiceTest for this portion[mention the topics or portion]."
     "Revise this chapter." →
     "Revise this chapter. The student wants a revision plan for the [name of the chapter(s)]"
    🛑 Avoid generic terms like “any DOST.”
   ✅ Always mention the specific DOST (practiceTest, formula, revision, etc.)and mention the portion clearly and most importantly only return the enriched dost in the translated text and not anywhere else not even in the structured answer.


• Harmful-Content Check: if any violence, abuse, or sexual content is detected, **stop** and return ONLY:
  {{
    "mode": "error",
    "error": "Harmful content detected"
  }}
• Translation: if translate_if_dost_or_mixed=True AND you classify mode as "dost" or "mixed", include:
  "translated": <English version of the original text>
• Emojis: inline emojis (😊,👍) are allowed inside 'paragraph' or 'heading'.
• Math: use `\(...\)` or `\[...\]` for inline or block LaTeX.

Available block types in your 'structured_answer':
  - heading: main title
  - subheading: section subtitle
  - paragraph: free text (LaTeX + emojis OK)
  - bold: one-line highlights
  - bullet: unordered lists
  - number: ordered lists
  - latex: { "latex": "<LaTeX string with delimiters>" }
    • Always emit a single field named `latex` whose value is a **string**, e.g.:
      {
        "latex": "\\\\( x^2 + y^2 = z^2 \\\\)"
      }
    • **Do not** emit `{ "latex": { "code": … } }` or `{ "latex": { "equation": … } }`.
  -ALWAYS STRICTLY FOLLOW,IMPORTANT: When emitting LaTeX or any content containing backslashes in your JSON strings, escape each backslash by doubling it.
    -For example, write '\\\\(' for '\\(', '\\\\sin' for '\\sin', and '\\\\frac' for '\\frac'.
    -This ensures the JSON you return parses cleanly.
    -And wrap your entire LaTeX string in a single `latex` field.  
    -Do **not** wrap it inside any sub-object.
  - table: {{ "headers": […], "rows": [[…],[…]] }} for comparisons
  - callout: {{ "style": "info"|"warning"|"tip", "content": … }}
  - definition: {{ "term": …, "definition": … }}
  - quote: {{ "content": …, "author"?: … }}
  - code: {{ "language": …, "code": … }}
  - IMPORTANT: For every stand-alone equation block, you **must** output exactly
                { "latex": "<escaped LaTeX>" }
                with no extra nesting. E.g.:
                ✔️ { "latex": "\\\\[ \\frac{a}{b} = c \\\\]" }
                ❌ { "latex": { "code": "\\\\[ \\frac{a}{b} = c \\\\]" } }
                ❌ { "latex": { "equation": "\\\\( x^2 \\\\)" } }
  / Example valid structured_answer snippet
"structured_answer": [
  { "heading": "Pythagorean Theorem" },
  { "latex": "\\\\[ a^2 + b^2 = c^2 \\\\]" },
  {"paragraph": "The Pythagorean theorem says that \\(a^2 + b^2 = c^2\\). This holds for all right triangles."}
]
Only return valid JSON matching the schema:
{{
  "mode": "general"|"dost"|"mixed"|"error",
  "error"?: "Harmful content detected",
  "structured_answer"?: [ …blocks… ],
  "translated"?: "English text"
}}
"""

    # Query-level instructions
    query_instructions = f"""
You must:

1. CAREFULLY analyze the STUDENT QUERY.

2. Detect if the query directly or indirectly indicates a need for DOST resources:
   - DOSTs include needs like Assignment, Test, Formula Sheet, Revision Plan, Speed Practice (clicking power, picking power, race dost), Concept Basket.
   - Phrases such as "help me study", "I want to revise", "give me practice", "give me revision plan", "give assignment" trigger DOST needs.
   - Any mention of formula, revision, practice, test, assignment, padhna hai, short notes, etc., implies DOST.

3. Detect if the query needs only general explanation (concept clarification, formula explanation, definitions, summaries, strategy, doubt resolution) or an exhaustive detailed explanation.

4. Recognize 3 possible cases:
   - Only DOSTs → Reply with {{ "mode": "dost" }}
   - Only general explanation → Reply with {{ "mode": "general", "structured_answer": [ … ] }}
   - Both explanation + DOSTs → Mixed → Reply with {{ "mode": "mixed", "structured_answer": [ … ] }}

⚡ Hint:
- If the query mentions what/why/how/define/explain/summarize AND assignment/test/formula/revision → Mixed.
- Mixed intent may be direct or implicit ("sikhao bhi aur assignment bhi do").
- Prefer identifying any dual-intent as Mixed.

5. For general/mixed, 'structured_answer' must include separate blocks:
   - paragraph, latex, bold, bullet, number

6. CONTEXT AWARENESS:
   - Assume JEE/NEET or Class 11/12 Board Exams,NCERT.
   - Adjust language and technical level: academic rigor, exam tips, strategy.
   - Include smart tips, exam strategies, cautionary notes as needed.
   - Add motivational one-liners when appropriate.
   - For exhaustive explanations, follow scientific standards.

7. TONE ADAPTATION:
   - Motivational and positive by default.
   - If user seems anxious/sad → extra motivational tone.
   - If user seems over-smart → witty yet respectful.
   - If neutral → warm and professional.

8. IMPORTANT:
   - NEVER invent DOST needs if not implied.
   - NEVER mix types inside one block.
   - Maintain clear format for frontend rendering.
   - Use proper LaTeX in paragraphs, numbers, bullets.

ONLY return valid JSON. DO NOT include any text outside the JSON.

=== STUDENT QUERY ===
{text}
"""

    messages = [
        {"role": "system", "content": system_instructions},
        {"role": "user",   "content": query_instructions}
    ]

    try:
        resp = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.0
        )
        content = resp.choices[0].message.content.strip()
        print("🔍 Raw GPT response:", content)

        # --- Extract JSON between fences if present ---
        if "```json" in content:
            content = content.split("```json")[-1].split("```",1)[0].strip()

        # … after you strip out the ```json fences …
        # First attempt
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            fixed = normalize_backslashes(content)
            return json.loads(fixed)

    except Exception as e:
        print(f"❌ query_checker() error: {e}")
        return {
            "mode": "general",
            "structured_answer": [
                {"type":"paragraph","content":"Sorry, we couldn't process your query due to an internal error. Please try again."}
            ]
        }

def normalize_backslashes(s: str) -> str:
    def repl(m):
        slashes = m.group(1)
        char   = m.group(2)
        # keep only the largest even count ≤ len(slashes)
        keep = (len(slashes)//2)*2
        return "\\" * keep + char
    # (\\+)([^"\\/bfnrtu]) => group1 = all slashes, group2 = next char
    return re.sub(r'(\\+)([^"\\/bfnrtu])', repl, s)

# ------------------------------
# 🧪 Local CLI Test Mode
# ------------------------------
if __name__ == "__main__":
    while True:
        q = input("Enter student query (or 'exit'): ")
        if q.lower() in ['exit', 'quit']:
            break
        out = query_checker(q, translate_if_dost_or_mixed=True, input_type="text")
        print(json.dumps(out, indent=2))
