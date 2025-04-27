# 📜 query_checker.py — Updated Version for DOST / General / Mixed Query Detection

import json
from openai import OpenAI

# Initialize OpenAI client
openai = OpenAI()

def query_checker(query_text: str) -> dict:
    """
    Decides if a query needs DOSTs, general explanation, or both (mixed).
    If general or mixed, returns structured answer ready for frontend rendering.
    """

    prompt = f"""
You are an intelligent academic backend agent for the ACADZA SuperDOST platform.

You must always:

1. CAREFULLY analyze the STUDENT QUERY.
2. Detect if the query directly or indirectly indicates a need for DOST resources:
   - DOSTs include needs like Assignment, Test, Formula Sheet, Revision Plan, Speed Practice (clicking power, picking power, race dost), Concept Basket.
   - If the student says things like "help me study", "I want to revise", "give me practice", "give me revision plan", "give assignment" etc., it means DOSTS ARE NEEDED.
   - If there is any slightest direct or indirect reference towards dosts like formula, revision, practice, test,assignment,padhna hai,short notes,etc., assume DOSTS ARE NEEDED.

3. Detect if the query needs only general explanation (concept clarification, formula explanation, definitions, summaries, strategy, doubt resolution).

4. 🔥 NEW INSTRUCTION: You must recognize 3 possible cases:
   - If the query needs only DOSTs → Reply with:
     ```json
     {{ "mode": "dost" }}
     ```

   - If the query needs only general conceptual explanation → Reply with:
     ```json
     {{ 
       "mode": "general", 
       "structured_answer": [ {{...}} ] 
     }}
     ```

   - If the query needs both explanation + DOSTs → classify it as Mixed Query → Reply with:
     ```json
     {{ 
       "mode": "mixed", 
       "structured_answer": [ {...} ] 
     }}
     ```

⚡ Hint for detection:
- If the query mentions concepts to be explained (what/why/how/define/explain/summarize) AND also asks for assignment/test/formula/revision → it's Mixed.
- Mixed intent could be direct OR hidden inside phrasing ("sikhao bhi aur assignment bhi do", "summary bhi do + test bhi").
- Prefer identifying even slightly implied dual-intent queries as Mixed.

5. For "general" or "mixed" modes, structured_answer must:
   - Have separate objects for each block:
     - paragraph (normal text)
     - latex (math expressions)
     - bold (important highlights)
     - bullet (important bullet points)
     - number (numbered steps)
     - emoji (motivational or summary emojis)

6. CONTEXT AWARENESS:
   - Always assume the student is preparing for JEE/NEET or Class 11/12 Board Exams.
   - Adjust language and technical level accordingly: academic rigor, exam tips, strategy.
   - Include small smart tips, exam strategies, cautionary notes if topic-specific.
   - If suitable, add motivational one-liners relevant to students' exam preparation journey.
   - If the query demands a certain level of exhaustive explanation then give it to them in a proper scientific way which follows their exam standards.

7. TONE ADAPTATION:
   - Highly motivational and positive by default.
   - If user seems anxious/sad → extra motivational tone.
   - If user seems over-smart → witty yet respectful reply.
   - If user is neutral → warm and professional tone.

8. IMPORTANT:
   - NEVER invent DOST needs if not implied.
   - NEVER mix types inside one block.
   - Maintain clear format so that frontend can render easily.
   - If equations come in paragraph,number,bullet then use proper latex notations to help fronend render easily.

ONLY return valid JSON.
DO NOT include greetings, explanations, or extra notes outside JSON.

=== STUDENT QUERY ===
{query_text}
"""

    try:
        # Call OpenAI Chat Completion
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()

        print("\n📝 Raw GPT Response:")
        print(content)  # 🛠️ Debug

        # 🛡️ Extract clean JSON safely
        if "```json" in content:
            content = content.split("```json")[-1].split("```", 1)[0].strip()

        parsed_response = json.loads(content)
        return parsed_response

    except Exception as e:
        print(f"❌ query_checker() failed: {e}")
        return {
            "mode": "general",
            "structured_answer": [
                {"type": "paragraph", "content": "Sorry, could not process the query properly due to an internal error."}
            ]
        }

# ------------------------------
# 🧪 Local CLI Test Mode
# ------------------------------
if __name__ == "__main__":
    while True:
        user_query = input("\n🎤 Enter a student query (or type 'exit' to quit):\n> ")
        if user_query.lower() in ["exit", "quit"]:
            break

        print("\n🔍 Running Query Checker...")
        result = query_checker(user_query)

        print("\n📦 Query Checker Output:")
        print(json.dumps(result, indent=2))
        print("\n" + "="*50)
