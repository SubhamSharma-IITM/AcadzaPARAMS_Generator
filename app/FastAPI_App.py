# 📜 FastAPI_App.py — Refactored with `process_dost_payload()` Helper

from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
import tempfile
import os
from openai import OpenAI
from app.main import run_orchestrator
from app.history_saver import save_query_history
from app.query_checker import query_checker

# -----------------------------
# 🔧 Setup
# -----------------------------
app = FastAPI()
openai = OpenAI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# -----------------------------
# 🤠 Whisper Transcriber
# -----------------------------
def transcribe_audio(file: UploadFile):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    print("🎿 Transcribing audio with Whisper...")
    with open(tmp_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    os.remove(tmp_path)
    return transcript.text

# -----------------------------
# 🛠️ DOST Processor Function
# -----------------------------
def process_dost_payload(query_text, student_id, auth_token):
    result = run_orchestrator(query_text)
    request_list = result.get("requestList", [])

    final_response_data = {}

    # Collect dost_steps mapping
    dost_steps = result.get("dost_steps", [])
    dost_step_map = {step.get("dost_type"): step.get("script", "") for step in dost_steps}

    for req in request_list:
        dost_type = req.get("bulkRequestType")
        title = req.get("title", "DOST")

        try:
            if dost_type == "concept":
                payload = {
                    "shorturl": req["shorturl"],
                    "longurl": req["longurl"],
                    "meta": req["meta"]
                }
                print(f"🌐 Creating shorturl for concept: {title}")
                resp = requests.post("https://api.acadza.in/shorturl/create", json=payload)
                resp.raise_for_status()
                longurl = resp.json()["urlshort"]["longurl"]
                full_url = f"https://acadza.com{longurl}"
                final_response_data.setdefault("concept", []).append({
                    "conceptLink": full_url,
                    "conceptTitle": title,
                    "script": dost_step_map.get("concept", "")
                })

            else:
                print(f"🛁 Calling combined API for: {title} [{dost_type}]")
                resp = requests.post("https://api.acadza.in/combined/create", json={"requestList": [req]})
                resp.raise_for_status()
                response_data = resp.json().get("data", {}).get(dost_type, {})

                if response_data:
                    dost_result = {}
                    if dost_type == "practiceTest":
                        dost_result = {
                            "practiceTestLink": response_data.get("testLink"),
                            "practiceTestTitle": response_data.get("testTitle", title),
                            "script": dost_step_map.get("practiceTest", "")
                        }
                    elif dost_type == "practiceAssignment":
                        dost_result = {
                            "practiceAssignmentLink": response_data.get("assignmentLink"),
                            "practiceAssignmentTitle": response_data.get("assignmentTitle", title),
                            "script": dost_step_map.get("practiceAssignment", "")
                        }
                    elif dost_type == "formula":
                        dost_result = {
                            "formulaLink": response_data.get("formulaLink"),
                            "formulaTitle": response_data.get("formulaTitle", title),
                            "script": dost_step_map.get("formula", "")
                        }
                    elif dost_type == "revision":
                        dost_result = {
                            "revisionLink": response_data.get("revisionLink"),
                            "revisionTitle": response_data.get("revisionTitle", title),
                            "script": dost_step_map.get("revision", "")
                        }
                    elif dost_type == "clickingPower":
                        dost_result = {
                            "clickingPowerLink": response_data.get("clickingLink"),
                            "clickingPowerTitle": response_data.get("clickingTitle", title),
                            "script": dost_step_map.get("clickingPower", "")
                        }
                    elif dost_type == "pickingPower":
                        dost_result = {
                            "pickingPowerLink": response_data.get("pickingLink"),
                            "pickingPowerTitle": response_data.get("pickingTitle", title),
                            "script": dost_step_map.get("pickingPower", "")
                        }
                    elif dost_type == "speedRace":
                        dost_result = {
                            "speedRaceLink": response_data.get("speedRaceLink"),
                            "speedRaceTitle": response_data.get("speedRaceTitle", title),
                            "script": dost_step_map.get("speedRace", "")
                        }

                    final_response_data.setdefault(dost_type, []).append(dost_result)

        except Exception as e:
            print(f"❌ API call failed for {dost_type}: {e}")

    # ✅ Save to History
    try:
        save_response = save_query_history(auth_token, result)
        print("📜 History saved: Status Code: ", save_response.statusCode)
    except Exception as e:
        print(f"❌ History saver failed: {e}")

    return final_response_data, result.get("queryResponseText", ""), result.get("queryAnalyzeText", "")

# -----------------------------
# ✅ Main Endpoint
# -----------------------------
@app.post("/process-query")
async def process_query(
    request: Request,
    file: UploadFile = File(None),
    query: str = Form(None)
):
    auth_token = request.headers.get("authorization")
    student_id = "65fc118510a22c2009134989"
    if not student_id or not auth_token:
        return {"error": "Missing student-id or Authorization token."}

    if file:
        query_text = transcribe_audio(file)
    elif query:
        query_text = query
    else:
        return {"error": "No query or file provided."}

    checker_result = query_checker(query_text)
    mode = checker_result.get("mode")

    if mode == "general":
        structured_answer = checker_result.get("structured_answer", [])
        return {
            "query": query_text,
            "result": {
                "status": "ok",
                "statusCode": 0,
                "isSuccessful": True,
                "statusMessage": "Success",
                "data": None
            },
            "reasoning": {
                "general_script": structured_answer,
                "analysis": "General Query Mode",
                "tone": "motivated"
            }
        }

    elif mode == "dost":
        final_response_data, main_script, analysis = process_dost_payload(query_text, student_id, auth_token)
        return {
            "query": query_text,
            "result": {
                "status": "ok",
                "statusCode": 0,
                "isSuccessful": True,
                "statusMessage": "Success",
                "data": final_response_data
            },
            "reasoning": {
                "main_script": main_script,
                "analysis": analysis,
                "tone": "motivated"
            }
        }

    elif mode == "mixed":
        structured_answer = checker_result.get("structured_answer", [])
        final_response_data, main_script, analysis = process_dost_payload(query_text, student_id, auth_token)
        return {
            "query": query_text,
            "result": {
                "status": "ok",
                "statusCode": 0,
                "isSuccessful": True,
                "statusMessage": "Success",
                "data": final_response_data
            },
            "reasoning": {
                "general_script": structured_answer,
                "main_script": main_script,
                "analysis": analysis,
                "tone": "motivated"
            }
        }

    else:
        return {"error": "Unable to classify query properly."}

# -----------------------------
# 🧪 Run locally for testing
# -----------------------------
if __name__ == "__main__":
    uvicorn.run("FastAPI_App:app", host="0.0.0.0", port=10000, reload=True)
