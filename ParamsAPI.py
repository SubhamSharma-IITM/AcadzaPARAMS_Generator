import os
import json
import uuid
import openai
import requests
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 Use "*" for development; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------
STUDENT_ID = ""
PRACTICE_ID = ""
CHAPTER_NAME = "Newton's law of motion"
SUBJECT = "Physics"

NLM_CONCEPT_TREE = {
    "Introduction to forces": ["Fundamental forces", "Normal, Tension and friction"],
    "Newton's law of motion": ["First law (Law of inertia)", "Momentum and its significance", "Second law", "Third law"],
    "Equilibrium of forces": ["Concurrent and Coplanar Forces", "Equilibrium of forces"],
    "Frame of reference": ["Inertial and non-inertial F.O.R.", "Pseudo Forces"],
    "Free body diagram": ["Fundamentals of drawing F.B.D.", "Train problems(Tension)", "Lift Problems(Normal)", "Wedge problems(Resolving Forces)"],
    "Constraint motion": ["String and pulley constraint(Tension)", "Wedge constraint(Normal)", "Rigid Body Constraint(Introduction)"],
    "Pulley problems": ["Simple pulley system", "Complex Pulley system", "Mechanical advantage"],
    "Spring": ["Spring constant", "Combination of Spring(parallel and series)", "Spring pulley system", "Equivalent Spring constant", "Cutting of spring and string."],
    "Pseudo force": ["Problems involving pseudo force"],
    "Friction": ["Types of Friction", "Direction of static and kinetic friction", "Coefficient of friction", "Limiting value of friction", "Angle of friction", "Transition of friction from static to kinetic", "Contact Force", "Angle of repose", "Two block problem", "Three or more block problem"],
    "Angle of repose": ["Motion on incline with angle more than angle of repose", "Motion on incline with less than the angle of repose", "Motion on vertical surface"],
    "Multiple block system": ["Concept of driving force", "Method to find which surface slips", "Method to find acceleration of blocks"]
}

ALL_CONCEPTS = list(NLM_CONCEPT_TREE.keys())

# ---------------------------------------------
def transcribe_voice(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcript.strip()

# ---------------------------------------------
def detect_dost_tasks(query):
    allowed_dosts = {
        "Concept Dost": ["Concept Revision Dost"],
        "Revision Dost": [],
        "Formula Dost": ["Formula Revision Dost"],
        "Practice Dost": ["Test Dost", "Assignment Dost"],
        "Speed Booster Dost": ["Clicking Dost", "Picking Dost", "Race Dost"]
    }

    prompt = f"""
You are an AI learning assistant that converts student queries into structured learning tasks (called DOSTs). These DOSTs help with study planning, revision, formulas, assignments, tests, and speed practice.

Your job is to:
1. Analyze the tone, urgency, keywords, and phrases from the query.
2. Match them to the most relevant DOST and Subdost from the list below.
3. Extract helpful parameters like 'concepts', 'difficulty', 'duration' if available.
4. Only trigger Speed Booster Dosts if tone is energetic, playful OR if keywords like “fast”, “timer”, “race”, “improve speed” are found
5. Having a test is NOT enough to trigger Practice Test Dost unless test-like practice is requested

🎯 OUTPUT FORMAT (Always reply in JSON):
[
  {{
    "Dost": "Revision Dost",
    "Subdost": null,
    "reason": "Student has a test and wants to revise concepts again.",
    "params": {{"concepts": ["Constraint motion", "Free body diagram"]}}
  }}
]

🧹 DOST & SUBDOST MAPPING:
{allowed_dosts}

📚 SCENARIO RULES:
- If query includes: "yaad nahi", "formulas chahiye", "revise formula" → use **Formula Dost**
- If query includes: "revise", "recap", "wapis padhna", "repeat", or tone = revision → **Revision Dost**
- If query includes: "test", "evaluate", "mains level", "mock paper", "60 mins" → **Practice Dost** + **Test Dost**
- If query includes: "assignment", "practice questions", "thoda solve karna", "easy questions" → **Practice Dost** + **Assignment Dost**
- If query includes: "first time", "padhna hai", "concepts samajh nahi aaye", "fundamentals unclear" → **Concept Dost**
- If query includes: "fast", "speed", "click", "reaction", "timer", "race", "attention test" → **Speed Booster Dost**
- If tone or wording suggests backlogs, confusion, multiple needs → include both **Formula + Revision Dost** as base
- Do NOT repeat the same DOST twice unless query clearly separates them.
- If no clear indicators are found, default to: **Formula + Revision Dost**

🧠 BEHAVIOR RULES:
- Never ask back for clarification.
- Assume chapter is Physics > Newton's Law unless mentioned otherwise.
- Use fallback: if no concepts mentioned, pick from: ["Constraint motion", "Free body diagram", "Friction", "Spring"]

🔠 SAMPLE QUERY:
{query}
"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    content = response.choices[0].message.content.strip()
    if "```json" in content:
        content = content.split("```json")[-1].split("```")[0].strip()
    return json.loads(content)


# ---------------------------------------------
def extract_subconcepts(concepts):
    subconcepts = []
    for concept in concepts:
        if concept in NLM_CONCEPT_TREE:
            for subconcept in NLM_CONCEPT_TREE[concept]:
                subconcepts.append({
                    "subject": SUBJECT,
                    "chapter": CHAPTER_NAME,
                    "concept": concept,
                    "subConcept": subconcept,
                    "area": "Red",
                    "importance": None
                })
    return subconcepts

#----------------------------------------------
def generate_audio_reasoning(query, tasks):
    reasoning_prompt = f"""
Act like a friendly, witty female Indian teacher who helps students. Based on the following student query and learning tasks, generate:
1. A short 20–30 sec voiceover script
2. A tone classification (e.g. chill, sad, confused, confident, motivated)
Respond in JSON format like:
{{
  "tone": "motivated",
  "script": "Since you're struggling... so I've added a Formula Dost..."
}}

Query: "{query}"

DOST Tasks: {json.dumps(tasks, indent=2)}
"""
    gpt_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": reasoning_prompt}],
        temperature=0.6
    )
    content = gpt_response.choices[0].message.content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {
        "tone": "neutral",
        "script": "Here's your study plan! You'll find your formula box, revision tasks and practice tests ready to go!"
    }


    try:
        audio_response = openai.audio.speech.create(
            model="tts-1",
            voice="shimmer",
            input=script
        )
        file_id = f"reasoning_{uuid.uuid4().hex}.mp3"
        file_path = f"static/{file_id}"
        with open(file_path, "wb") as f:
            f.write(audio_response.content)
        return script, f"/static/{file_id}", parsed.get("tone", "neutral")
    except Exception as e:
        return script, None, parsed.get("tone", "neutral")

# ---------------------------------------------
def build_formula():
    formula_cart = []
    for concept, subs in NLM_CONCEPT_TREE.items():
        for sub in subs:
            formula_cart.append({"subject": SUBJECT, "chapter": CHAPTER_NAME, "concept": concept, "subConcept": sub})
    return {"studentid": STUDENT_ID, "title": "NLMF", "formulaCart": formula_cart}

# ---------------------------------------------
def build_test(concepts, level="EASY", time=60):
    return {
        "userId": STUDENT_ID,
        "practiceType": "test",
        "title": "NLMT1",
        "paperPattern": "Mains",
        "level": level.upper(),
        "natureOfTest": "Random",
        "noOfMinutes": time,
        "coachingView": "PACE",
        "batchs": [],
        "sectionOrder": ["singleQuestions", "multipleQuestions", "integerQuestions", "passageQuestions", "matchQuestions"],
        "passageQuestionLimit": 3,
        "isNCERT": False,
        "helpRequired": False,
        "isMultiple": False,
        "practicePortion": [{"id": PRACTICE_ID, "content": {"subject": SUBJECT, "chapter": CHAPTER_NAME, "concept": concept}} for concept in concepts]
    }

# ---------------------------------------------
def build_revision(concepts):
    return {
        "title": "NLM Revision Plan",
        "allotedDay": 1,
        "allotedTime": 1,
        "strategy": 1,
        "daywisePortion": {
            "day1": {
                "portion": [{
                    "weakData": extract_subconcepts(concepts),
                    "subject": SUBJECT,
                    "chapter": CHAPTER_NAME,
                    "concept": concept,
                    "importance": None,
                    "ratio": None,
                    "area": "Red",
                    "time": 60,
                    "star": 1,
                    "task": [{"type": "assignment", "completed": False}, {"type": "test", "completed": False}],
                    "impratio": 3
                } for concept in concepts]
            }
        }
    }

# ---------------------------------------------
def build_assignment(concepts):
    return {
        "userId": STUDENT_ID,
        "practiceType": "assignment",
        "title": "NLMA",
        "isNCERT": False,
        "level": "EASY",
        "assignmentQuesCount": {"scq": 20, "mcq": 0, "integerQuestion": 5, "passageQuestion": 0, "matchQuestion": 0},
        "practicePortion": [{"id": PRACTICE_ID, "content": {"subject": SUBJECT, "chapter": CHAPTER_NAME, "concept": concept}} for concept in concepts]
    }

# ---------------------------------------------
def build_clicking():
    return {"user": STUDENT_ID, "chapters": [CHAPTER_NAME], "totalQuestions": "10", "subject": SUBJECT}

# ---------------------------------------------
def build_picking():
    return {"user": STUDENT_ID, "chapter": CHAPTER_NAME, "subject": SUBJECT}

# ---------------------------------------------
def build_race():
    return {"subject": SUBJECT, "chapters": [CHAPTER_NAME], "totalQuestions": 15, "scheduledTime": "", "duration": "", "opponentType": "bot", "rank": 100}

# ---------------------------------------------
@app.post("/process-query")
async def process_query_api(file: UploadFile = File(...)):
    contents = await file.read()
    with open("temp.wav", "wb") as f:
        f.write(contents)
    query = transcribe_voice("temp.wav")
    tasks = detect_dost_tasks(query)

    requestList = []
    fallback_concepts = []

    for task in tasks:
        dost = task.get("Dost")
        subdost = task.get("Subdost")
        params = task.get("params", {})
        concepts = params.get("concepts", [])
        if not concepts:
            concepts = fallback_concepts or ALL_CONCEPTS
        else:
            fallback_concepts = concepts

        if dost == "Formula Dost":
            requestList.append({"bulkRequestType": "formula", **build_formula()})
        elif dost == "Revision Dost":
            requestList.append({"bulkRequestType": "revision", **build_revision(concepts)})
        elif dost == "Practice Dost" and subdost == "Test Dost":
            requestList.append({"bulkRequestType": "practiceTest", **build_test(concepts, params.get("difficulty", "EASY"), int(str(params.get("duration", "60")).split()[0]))})
        elif dost == "Practice Dost" and subdost == "Assignment Dost":
            requestList.append({"bulkRequestType": "practiceAssignment", **build_assignment(concepts)})
        elif dost == "Speed Booster Dost" and subdost == "Clicking Dost":
            requestList.append({"bulkRequestType": "clickingPower", **build_clicking()})
        elif dost == "Speed Booster Dost" and subdost == "Picking Dost":
            requestList.append({"bulkRequestType": "pickingPower", **build_picking()})
        elif dost == "Speed Booster Dost" and subdost == "Race Dost":
            requestList.append({"bulkRequestType": "speedRace", **build_race()})

    acadza_response = requests.post("https://api.acadza.in/combined/create", json={"requestList": requestList})

    reasoning_text, audio_url, tone = generate_audio_reasoning(query, tasks)

    return JSONResponse(content={
        "query": query,
        "result": acadza_response.json(),
        "reasoning_text": reasoning_text,
        "reasoning_audio_url": audio_url,
        "detected_tone": tone
    })
