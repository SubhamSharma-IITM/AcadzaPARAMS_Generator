# 📜 query_checker.py — Determines if query needs DOST or direct answer

import json
from openai import OpenAI

# Initialize OpenAI client
openai = OpenAI()

def query_checker(query_text: str) -> dict:
    """
    Decides if a query needs DOSTs or is a general question.
    If general, returns a structured answer ready for frontend rendering.
    """

    prompt = f"""
You are an intelligent academic backend agent for the ACADZA SuperDOST platform.

You must always:

1. CAREFULLY analyze the STUDENT QUERY.
2. Detect if the query directly or indirectly indicates a need for DOST resources:
   - DOSTs include needs like Assignment, Test, Formula Sheet, Revision Plan, Speed Practice, Concept Basket.
   - If the student says things like "help me study", "I want to revise", "give me practice", "give me revision plan", "give assignment" etc., it means DOSTS ARE NEEDED.

3. If DOSTS are needed:
   - Reply ONLY with:
     ```json
     {{ "dosts_needed": true }}
     ```

4. If DOSTS are NOT needed (it is a general information, definition, formula, exam cutoff, small conceptual clarification, motivational doubt, etc):
   - Reply ONLY with:
     ```json
     {{
       "dosts_needed": false,
       "structured_answer": [
         {{ "type": "paragraph", "content": "normal text" }},
         {{ "type": "latex", "content": "latex equation here" }},
         {{ "type": "bold", "content": "bold text here" }},
         {{ "type": "bullet", "content": "bullet point text" }},
         {{ "type": "number", "content": "numbered list text" }},
         {{ "type": "emoji", "content": "emoji text" }}
       ]
     }}
     ```
   - Each paragraph or element must be a separate object.
   - Strictly label each part using "type" as shown.
   - No merging of types inside content.
   - If multiple paragraphs, use multiple "paragraph" objects.

5. CONTEXT AWARENESS:
   - Always assume the student is preparing for **JEE/NEET** or **Class 11/12 Board Exams**.
   - Adjust your language to match this level.
   - Include small smart tips, exam strategies, cautionary notes if topic-specific.
   - If suitable, add motivational one-liners.

6. TONE ADAPTATION:
   - Highly motivational and positive by default.
   - If user seems anxious/sad → extra motivational tone.
   - If user seems over-smart → witty yet respectful reply.
   - If user is neutral → warm and professional tone.

7. IMPORTANT:
   - NEVER invent DOST needs if not implied.
   - NEVER mix types inside one block.
   - Maintain clear format so that frontend can render easily.

ONLY return valid JSON.
DO NOT include greetings, explanations, extra notes outside JSON.

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
            content = content.split("```json")[-1].split("```")[0].strip()

        parsed_response = json.loads(content)
        return parsed_response

    except Exception as e:
        print(f"❌ query_checker() failed: {e}")
        return {
            "dosts_needed": False,
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
