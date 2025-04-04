import os
import json
import openai
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# ---------------------------------------------------------------
NLM_CONCEPT_TREE = {
    "Introduction to forces": [
        "Fundamental forces",
        "Normal, Tension and friction"
    ],
    "Newton's law of motion": [
        "First law (Law of inertia)",
        "Momentum and its significance",
        "Second law",
        "Third law"
    ],
    "Equilibrium of forces": [
        "Concurrent and Coplanar Forces",
        "Equilibrium of forces"
    ],
    "Frame of reference": [
        "Inertial and non-inertial F.O.R.",
        "Pseudo Forces"
    ],
    "Free body diagram": [
        "Fundamentals of drawing F.B.D.",
        "Train problems(Tension)",
        "Lift Problems(Normal)",
        "Wedge problems(Resolving Forces)"
    ],
    "Constraint motion": [
        "String and pulley constraint(Tension)",
        "Wedge constraint(Normal)",
        "Rigid Body Constraint(Introduction)"
    ],
    "Pulley problems": [
        "Simple pulley system",
        "Complex Pulley system",
        "Mechanical advantage"
    ],
    "Spring": [
        "Spring constant",
        "Combination of Spring(parallel and series)",
        "Spring pulley system",
        "Equivalent Spring constant",
        "Cutting of spring and string."
    ],
    "Pseudo force": [
        "Problems involving pseudo force"
    ],
    "Friction": [
        "Types of Friction",
        "Direction of static and kinetic friction",
        "Coefficient of friction",
        "Limiting value of friction",
        "Angle of friction",
        "Transition of friction from static to kinetic",
        "Contact Force",
        "Angle of repose",
        "Two block problem",
        "Three or more block problem"
    ],
    "Angle of repose": [
        "Motion on incline with angle more than angle of repose",
        "Motion on incline with less than the angle of repose",
        "Motion on vertical surface"
    ],
    "Multiple block system": [
        "Concept of driving force",
        "Method to find which surface slips",
        "Method to find acceleration of blocks"
    ]
}

ALL_CONCEPTS = list(NLM_CONCEPT_TREE.keys())

# ---------------------------------------------------------------
def detect_dost_tasks(query):
    allowed_dosts = {
        "Concept Dost": ["Concept Revision Dost"],
        "Revision Dost": [],
        "Formula Dost": ["Formula Revision Dost"],
        "Practice Dost": ["Test Dost", "Assignment Dost"]
    }

    prompt = f"""
You are a task extractor for a student learning system. Extract educational needs from this query.
Respond in JSON with a list of tasks. Each task must include:
- Dost (Choose one from {list(allowed_dosts.keys())})
- Subdost (Only if applicable from its allowed list: {allowed_dosts})
- Brief reason
- Extracted params (concepts, difficulty, duration, etc.)
Query: {query}
"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    content = response.choices[0].message.content.strip()
    if "```json" in content:
        content = content.split("```json")[-1].split("```")[0].strip()
    return json.loads(content)

# ---------------------------------------------------------------
def extract_subconcepts(concepts):
    subconcepts = []
    for concept in concepts:
        if concept in NLM_CONCEPT_TREE:
            for subconcept in NLM_CONCEPT_TREE[concept]:
                subconcepts.append({
                    "subject": "Physics",
                    "chapter": "Newton's law of motion",
                    "concept": concept,
                    "subConcept": subconcept,
                    "area": "Red",
                    "importance": None
                })
    return subconcepts

# ---------------------------------------------------------------
def build_formula_dost():
    formula_cart = []
    for concept, sublist in NLM_CONCEPT_TREE.items():
        for sub in sublist:
            formula_cart.append({
                "subject": "Physics",
                "chapter": "Newton's law of motion",
                "concept": concept,
                "subConcept": sub
            })
    return {
        "studentid": "",
        "title": "NLMF",
        "formulaCart": formula_cart
    }

# ---------------------------------------------------------------
def build_test_dost(concepts, level="EASY", time=60):
    return {
        "userId": "",
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
        "practicePortion": [
            {
                "id": "",
                "content": {
                    "subject": "Physics",
                    "chapter": "Newton's law of motion",
                    "concept": concept
                }
            } for concept in concepts
        ]
    }

# ---------------------------------------------------------------
def build_revision_dost(concepts):
    return {
        "title": "NLM Revision Plan",
        "allotedDay": 1,
        "allotedTime": 1,
        "strategy": 1,
        "daywisePortion": {
            "day1": {
                "portion": [
                    {
                        "weakData": extract_subconcepts(concepts),
                        "subject": "Physics",
                        "chapter": "Newton's law of motion",
                        "concept": concept,
                        "importance": None,
                        "ratio": None,
                        "area": "Red",
                        "time": 60,
                        "star": 1,
                        "task": [
                            {"type": "assignment", "completed": False},
                            {"type": "test", "completed": False}
                        ],
                        "impratio": 3
                    } for concept in concepts
                ]
            }
        }
    }

# ---------------------------------------------------------------
@app.post("/process-query")
async def process_query_api(file: UploadFile = File(...)):
    contents = await file.read()
    with open("temp.wav", "wb") as f:
        f.write(contents)

    query = transcribe_voice("temp.wav")
    tasks = detect_dost_tasks(query)
    results = []

    for task in tasks:
        dost = task.get("Dost")
        subdost = task.get("Subdost")
        params = task.get("params", {})
        concepts = params.get("concepts", ALL_CONCEPTS if dost == "Formula Dost" else [])

        if dost == "Formula Dost":
            results.append({"Dost": dost, "Subdost": subdost, "data": build_formula_dost()})
        elif dost == "Revision Dost":
            results.append({"Dost": dost, "Subdost": subdost, "data": build_revision_dost(concepts)})
        elif dost == "Practice Dost" and subdost == "Test Dost":
            minutes = int(str(params.get("duration", "60 minutes")).split()[0])
            level = params.get("difficulty", "EASY")
            results.append({"Dost": dost, "Subdost": subdost, "data": build_test_dost(concepts, level, minutes)})
        else:
            results.append({"error": f"Unhandled Dost: {dost} / {subdost}"})

    return JSONResponse(content={"query": query, "result": results})

# ---------------------------------------------------------------
def transcribe_voice(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcript.strip()
