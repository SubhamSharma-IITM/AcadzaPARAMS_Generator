import uuid

from app.modules.utils import get_concepts, get_subconcepts, build_practice_portion

# -------------------------
# ✅ INDIVIDUAL BUILDERS (with student_id injection)
# -------------------------

def build_assignment(subject, chapter_groups, params, student_id):
    chapters_seen = set()
    title = " + ".join([
        g["chapter"] for g in chapter_groups
        if not (g["chapter"] in chapters_seen or chapters_seen.add(g["chapter"]))
    ]) + " Assignment"

    return {
        "bulkRequestType": "practiceAssignment",
        "userId": student_id,
        "practiceType": "assignment",
        "title": title,
        "isNCERT": params.get("isNCERT"),
        "level": params.get("difficulty", "easy").upper(),
        "assignmentQuesCount": params.get("type_split", {
            "scq": 10, "mcq": 10, "integerQuestion": 0, "passageQuestion": 0, "matchQuestion": 0
        }),
        "practicePortion": build_practice_portion(chapter_groups)
    }

def build_test(subject, chapter_groups, params, student_id):
    chapters_seen = set()
    title = " + ".join([
        g["chapter"] for g in chapter_groups
        if not (g["chapter"] in chapters_seen or chapters_seen.add(g["chapter"]))
    ]) + " Test"

    portion = build_practice_portion(chapter_groups)
    return {
        "bulkRequestType": "practiceTest",
        "userId": student_id,
        "practiceType": "test",
        "title": title,
        "paperPattern": params.get("paperPattern", "Mains"),
        "level": params.get("difficulty", "easy").upper(),
        "natureOfTest": "Random",
        "noOfMinutes": params.get("duration_minutes", 60),
        "coachingView": "PACE",
        "batchs": [],
        "sectionOrder": ["singleQuestions", "multipleQuestions", "integerQuestions", "passageQuestions", "matchQuestions"],
        "passageQuestionLimit": 3,
        "isNCERT": params.get("isNCERT"),
        "helpRequired": False,
        "isMultiple": False,
        "practicePortion": portion
    }

def build_formula(subject, chapter_groups, student_id):
    formula_cart = []

    for group in chapter_groups:
        chapter = group["chapter"]
        concepts = group.get("concepts", [])
        subconcepts = group.get("subconcepts", {})
        subject = group.get("subject")

        for concept in concepts:
            subs = subconcepts.get(concept, [])
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

    chapters_seen = set()
    title = " + ".join([
        g["chapter"] for g in chapter_groups
        if not (g["chapter"] in chapters_seen or chapters_seen.add(g["chapter"]))
    ]) + " Formula Sheet"

    return {
        "bulkRequestType": "formula",
        "studentid": student_id,
        "title": title,
        "formulaCart": formula_cart
    }

def build_revision(subject, chapter_groups, params, student_id):
    chapters_seen = set()
    title = " + ".join([
        g["chapter"] for g in chapter_groups
        if not (g["chapter"] in chapters_seen or chapters_seen.add(g["chapter"]))
    ]) + " Revision Plan"

    importance_map = params.get("importance", {})
    alloted_days = params.get("allotedDay", 3)
    portion_items = []

    for group in chapter_groups:
        chapter = group["chapter"]
        concepts = group.get("concepts", [])
        subconcepts = group.get("subconcepts", {})

        for concept in concepts:
            imp = importance_map
            weak_data = [
                {
                    "subject": subject,
                    "chapter": chapter,
                    "concept": concept,
                    "subConcept": sub,
                    "area": "Red",
                    "importance": imp
                } for sub in subconcepts.get(concept, [])
            ] or [{
                "subject": subject,
                "chapter": chapter,
                "concept": concept,
                "subConcept": "",
                "area": "Red",
                "importance": imp
            }]
            portion_items.append({
                "subject": subject,
                "chapter": chapter,
                "concept": concept,
                "importance": imp,
                "ratio": None,
                "area": "Red",
                "time": params.get("daywiseTimePerPortion", 60),
                "star": 1,
                "task": [
                    {"type": "assignment", "completed": False},
                    {"type": "test", "completed": False}
                ],
                "impratio": 3,
                "weakData": weak_data
            })

    daywisePortion = {}
    items_per_day = max(1, len(portion_items) // alloted_days)
    for day in range(1, alloted_days + 1):
        start_idx = (day - 1) * items_per_day
        end_idx = start_idx + items_per_day if day != alloted_days else len(portion_items)
        daywisePortion[f"day{day}"] = {"portion": portion_items[start_idx:end_idx]}

    return {
        "bulkRequestType": "revision",
        "userId": student_id,
        "title": title,
        "allotedDay": alloted_days,
        "allotedTime": params.get("allotedTime", 1),
        "strategy": params.get("strategy", 1),
        "daywisePortion": daywisePortion
    }

def build_clicking(subject, chapter, student_id):
    return {
        "bulkRequestType": "clickingPower",
        "user": student_id,
        "chapters": [chapter],
        "subject": subject,
        "totalQuestions": "10"
    }

def build_picking(subject, chapter, student_id):
    return {
        "bulkRequestType": "pickingPower",
        "user": student_id,
        "chapter": chapter,
        "subject": subject
    }

def build_race(subject, chapter, student_id):
    return {
        "bulkRequestType": "speedRace",
        "subject": subject,
        "chapters": [chapter],
        "totalQuestions": 15,
        "scheduledTime": "",
        "duration": "",
        "opponentType": "bot",
        "rank": 100,
        "user": student_id
    }

def build_concept(subject, chapter_groups, student_id):
    import uuid
    concept_basket_data = []
    seen_concept_subconcept = set()

    print("\n🔎 START build_concept Dry Run:")
    print(f"Received chapter_groups:\n{chapter_groups}\n")

    for group in chapter_groups:
        chapter = group["chapter"]
        requested_concepts = group.get("concepts", [])
        requested_subconcepts = group.get("subconcepts", {})

        print(f"📚 Chapter: {chapter}")
        print(f"🎯 Requested Concepts: {requested_concepts}")
        print(f"🎯 Requested Subconcepts: {requested_subconcepts}")

        for concept in requested_concepts:
            subs = requested_subconcepts.get(concept, [])
            if not subs:
                key = (chapter, concept, "")
                if key not in seen_concept_subconcept:
                    print(f"➕ Adding concept (no subconcepts): {concept}")
                    concept_basket_data.append({
                        "subject": subject,
                        "subSubject": subject,
                        "chapter": chapter,
                        "concept": concept,
                        "subConcept": ""
                    })
                    seen_concept_subconcept.add(key)
            else:
                for sub in subs:
                    key = (chapter, concept, sub)
                    if key not in seen_concept_subconcept:
                        print(f"➕ Adding subconcept: {concept} ➔ {sub}")
                        concept_basket_data.append({
                            "subject": subject,
                            "subSubject": subject,
                            "chapter": chapter,
                            "concept": concept,
                            "subConcept": sub
                        })
                        seen_concept_subconcept.add(key)

    print("\n✅ Final Concept Basket Data:")
    for item in concept_basket_data:
        print(item)

    chapters_seen = set()
    chapter_title = " + ".join([
        g["chapter"] for g in chapter_groups
        if not (g["chapter"] in chapters_seen or chapters_seen.add(g["chapter"]))
    ])

    unique_id = str(uuid.uuid4())
    shorturl = f"cb-{unique_id}"
    longurl = f"/dosts/share-concept-basket/view/{shorturl}"

    return {
        "bulkRequestType": "concept",
        "studentid": student_id,
        "shorturl": shorturl,
        "longurl": longurl,
        "title": f"{chapter_title} Concept Basket",
        "meta": {
            "chapter": chapter_title,
            "discription": "Concept Basket",
            "conceptBasketData": concept_basket_data
        }
    }


# -------------------------
# 🧠 FINAL PAYLOAD ROUTER
# -------------------------
def build_payload(dost_type, request, student_id):
    chapter_groups = request.get("chapter_groups", [])
    subject = request.get("subject")
    params = request

    if dost_type == "practiceTest":
        print(build_test(subject, chapter_groups, params, student_id))
        return build_test(subject, chapter_groups, params, student_id)
    elif dost_type == "practiceAssignment":
        return build_assignment(subject, chapter_groups, params, student_id)
    elif dost_type == "formula":
        return build_formula(subject, chapter_groups, student_id)
    elif dost_type == "revision":
        return build_revision(subject, chapter_groups, params, student_id)
    elif dost_type == "concept":
        return build_concept(subject, chapter_groups, student_id)

    payloads = []
    for group in chapter_groups:
        chapter = group.get("chapter")
        subject = group.get("subject")
        if dost_type == "clickingPower":
            payloads.append(build_clicking(subject, chapter, student_id))
        elif dost_type == "pickingPower":
            payloads.append(build_picking(subject, chapter, student_id))
        elif dost_type == "speedRace":
            payloads.append(build_race(subject, chapter, student_id))

    if not payloads:
        return None
    else:
        return payloads


if __name__ == "__main__":
    # 📚 Define sample inputs

    # Clicking Power Test
    req_clicking = {
        "subject": "Physics",
        "chapter": "Current Electricity"
    }

    # Picking Power Test
    req_picking = {
        "subject": "Chemistry",
        "chapter": "Chemical Kinetics"
    }

    # Speed Race Test
    req_speed = {
        "subject": "Physics",
        "chapter": "Motion in one dimension"
    }

    # 🧠 Student ID
    student_id = "test_student_123"

    # 🛠️ Test build_clicking
    print("\n🔵 Clicking Power Payload:")
    output_clicking = build_clicking(req_clicking["subject"], req_clicking["chapter"], student_id)
    print(output_clicking)

    # 🛠️ Test build_picking
    print("\n🟣 Picking Power Payload:")
    output_picking = build_picking(req_picking["subject"], req_picking["chapter"], student_id)
    print(output_picking)

    # 🛠️ Test build_race
    print("\n🔴 Speed Race Payload:")
    output_race = build_race(req_speed["subject"], req_speed["chapter"], student_id)
    print(output_race)


