import requests

# -----------------------------
# 🧠 Extract flat portion data from requestList
# -----------------------------
def extract_portion_from_requestList(request_list):
    portion = []
    for req in request_list:
        chapter_groups = req.get("chapter_groups", [])
        for group in chapter_groups:
            subject = group.get("subject", "")
            chapter = group.get("chapter", "")
            concepts = group.get("concepts", [])
            subconcepts_map = group.get("subconcepts", {})

            if not concepts:
                portion.append({
                    "subject": subject,
                    "chapter": chapter,
                    "concept": "",
                    "subConcept": ""
                })
            else:
                for concept in concepts:
                    subconcepts = subconcepts_map.get(concept, [])
                    if not subconcepts:
                        portion.append({
                            "subject": subject,
                            "chapter": chapter,
                            "concept": concept,
                            "subConcept": ""
                        })
                    else:
                        for sub in subconcepts:
                            portion.append({
                                "subject": subject,
                                "chapter": chapter,
                                "concept": concept,
                                "subConcept": sub
                            })
    return portion

# -----------------------------
# 📜 save_query_history()
# -----------------------------
def save_query_history(auth_token: str, result: dict):
    """
    Sends a POST request to the gpthistory/create API using orchestrator result.
    Automatically extracts all needed fields.
    """
    url = "https://api.acadza.in/gpthistory/create"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }

    request_list = result.get("requestList", [])
    portions = extract_portion_from_requestList(request_list)
    query_name = result.get("raw_query", "Student Query")
    if len(query_name) > 500:
        print(f"⚠️ Query name too long ({len(query_name)} chars), trimming to 500.")
        query_name = query_name[:500]

    # Extract first subject/chapter as overview
    first_subject = ""
    first_chapter = ""
    if request_list:
        first_task = request_list[0]
        chapter_groups = first_task.get("chapter_groups", [])
        if chapter_groups:
            first_subject = chapter_groups[0].get("subject", "")
            first_chapter = chapter_groups[0].get("chapter", "")

    payload = {
        "queryName": query_name.strip(),
        "portion": portions,
        "subject": first_subject,
        "chapter": first_chapter,
        "queryAnalyzeText": result.get("queryAnalyzeText", ""),
        "queryResponseText": result.get("queryResponseText", "")
    }

    try:
        print("\n📡 Sending history API request...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("✅ History saved successfully!")
        return response.json()
    except requests.exceptions.HTTPError as errh:
        print("❌ HTTP Error:", errh)
        return {"error": "HTTP Error", "details": str(errh)}
    except requests.exceptions.RequestException as err:
        print("❌ Request Error:", err)
        return {"error": "Request Failed", "details": str(err)}