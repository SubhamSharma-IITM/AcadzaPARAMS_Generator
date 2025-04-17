import uuid
import json
from modules.utils import get_concepts, get_subconcepts, build_practice_portion

# -------------------------
# ✅ INDIVIDUAL BUILDERS
# -------------------------

def build_assignment(subject, chapter, concepts, params, subconcepts):
    return {
        "bulkRequestType": "practiceAssignment",
        "userId": "",
        "practiceType": "assignment",
        "title": f"{chapter} Assignment",
        "isNCERT": False,
        "level": params.get("difficulty", "easy").upper(),
        "assignmentQuesCount": params.get("type_split", {
            "scq": 10, "mcq": 10, "integerQuestion": 0, "passageQuestion": 0, "matchQuestion": 0
        }),
        "practicePortion": build_practice_portion([{
            "subject": subject,
            "chapter": chapter,
            "concepts": concepts,
            "subconcepts": subconcepts
        }])
    }

def build_test(subject, chapter, concepts, params, subconcepts):
    return {
        "bulkRequestType": "practiceTest",
        "userId": "",
        "practiceType": "test",
        "title": f"{chapter} Test",
        "paperPattern": "Mains",
        "level": params.get("difficulty", "easy").upper(),
        "natureOfTest": "Random",
        "noOfMinutes": params.get("duration_minutes", 60),
        "coachingView": "PACE",
        "batchs": [],
        "sectionOrder": ["singleQuestions", "multipleQuestions", "integerQuestions", "passageQuestions", "matchQuestions"],
        "passageQuestionLimit": 3,
        "isNCERT": False,
        "helpRequired": False,
        "isMultiple": False,
        "practicePortion": build_practice_portion([{
            "subject": subject,
            "chapter": chapter,
            "concepts": concepts,
            "subconcepts": subconcepts
        }])
    }

def build_formula(subject, chapter, concepts, subconcepts=None):
    formula_cart = []
    for concept in concepts:
        subs = subconcepts.get(concept, []) if subconcepts else []
        if not subs:
            formula_cart.append({
                "id": str(uuid.uuid4()),
                "content": {
                    "subject": subject,
                    "chapter": chapter,
                    "concept": concept,
                    "subConcept": "",
                    "text": concept,
                    "selected": True,
                    "disabled": False
                }
            })
        for sub in subs:
            formula_cart.append({
                "id": str(uuid.uuid4()),
                "content": {
                    "subject": subject,
                    "chapter": chapter,
                    "concept": concept,
                    "subConcept": sub,
                    "text": sub,
                    "selected": True,
                    "disabled": False
                }
            })
    return {
        "bulkRequestType": "formula",
        "studentid": "",
        "title": f"{chapter} Formula Sheet",
        "formulaCart": formula_cart
    }

def build_revision(subject, chapter, concepts, subconcepts):
    return {
        "bulkRequestType": "revision",
        "title": f"{chapter} Revision Plan",
        "allotedDay": 1,
        "allotedTime": 1,
        "strategy": 1,
        "daywisePortion": {
            "day1": {
                "portion": [
                    {
                        "subject": subject,
                        "chapter": chapter,
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
                        "impratio": 3,
                        "weakData": [
                            {
                                "subject": subject,
                                "chapter": chapter,
                                "concept": concept,
                                "subConcept": sub,
                                "area": "Red",
                                "importance": None
                            } for sub in subconcepts.get(concept, [])
                        ] or [{
                            "subject": subject,
                            "chapter": chapter,
                            "concept": concept,
                            "subConcept": "",
                            "area": "Red",
                            "importance": None
                        }]
                    } for concept in concepts
                ]
            }
        }
    }

def build_clicking(subject, chapter):
    return {
        "bulkRequestType": "clickingPower",
        "user": "",
        "chapters": [chapter],
        "subject": subject,
        "totalQuestions": "10"
    }

def build_picking(subject, chapter):
    return {
        "bulkRequestType": "pickingPower",
        "user": "",
        "chapter": chapter,
        "subject": subject
    }

def build_race(subject, chapter):
    return {
        "bulkRequestType": "speedRace",
        "subject": subject,
        "chapters": [chapter],
        "totalQuestions": 15,
        "scheduledTime": "",
        "duration": "",
        "opponentType": "bot",
        "rank": 100
    }

def build_concept(subject, chapter, concepts, subconcepts):
    unique_id = str(uuid.uuid4())
    shorturl = f"cb-{unique_id}"
    longurl = f"/dosts/share-concept-basket/view/{shorturl}"
    concept_basket_data = []
    for concept in concepts:
        subs = subconcepts.get(concept, [])
        if not subs:
            concept_basket_data.append({
                "subject": subject,
                "subSubject": subject,
                "chapter": chapter,
                "concept": concept,
                "subConcept": ""
            })
        for sub in subs:
            concept_basket_data.append({
                "subject": subject,
                "subSubject": subject,
                "chapter": chapter,
                "concept": concept,
                "subConcept": sub
            })
    return {
        "bulkRequestType": "concept",
        "shorturl": shorturl,
        "longurl": longurl,
        "meta": {
            "chapter": chapter,
            "discription": "Concept Basket",
            "conceptBasketData": concept_basket_data
        }
    }

# -------------------------
# 🧠 BUILD PAYLOAD ROUTER
# -------------------------

def build_payload(dost_type, request, tree):
    chapter = request.get("chapter")
    subject = request.get("subject")
    concepts = request.get("concepts") or get_concepts(subject, chapter)
    subconcepts = {c: get_subconcepts(subject, chapter, c) for c in concepts}

    if not chapter or not subject:
        print(f"❌ Skipping build: Missing chapter or subject → Chapter: {chapter}, Subject: {subject}")
        return None

    if not concepts:
        print(f"⚠️ WARNING: No concepts found for {chapter} ({subject})")

    if dost_type == "practiceAssignment":
        payload = build_assignment(subject, chapter, concepts, request, subconcepts)
    elif dost_type == "practiceTest":
        payload = build_test(subject, chapter, concepts, request, subconcepts)
    elif dost_type == "formula":
        payload = build_formula(subject, chapter, concepts, subconcepts)
    elif dost_type == "revision":
        payload = build_revision(subject, chapter, concepts, subconcepts)
    elif dost_type == "clickingPower":
        payload = build_clicking(subject, chapter)
    elif dost_type == "pickingPower":
        payload = build_picking(subject, chapter)
    elif dost_type == "speedRace":
        payload = build_race(subject, chapter)
    elif dost_type == "concept":
        payload = build_concept(subject, chapter, concepts, subconcepts)
    else:
        payload = None

    if payload:
        print(f"\n📦 Built Payload for {dost_type} ({chapter}):")
        print(json.dumps(payload, indent=2))

    return payload
