from fastapi import FastAPI, File, Form, UploadFile, Request, Header
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests
import tempfile
import os
from openai import OpenAI
from app.main import run_orchestrator
from app.history_saver import save_query_history


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

# Enable Swagger auth header



# -----------------------------
# 🧠 Whisper Transcriber
# -----------------------------
def transcribe_audio(file: UploadFile):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    print("🎧 Transcribing audio with Whisper...")
    with open(tmp_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    os.remove(tmp_path)
    return transcript.text

# -----------------------------
# ✅ Main Endpoint
# -----------------------------
@app.post("/process-query")
async def process_query(
    request: Request,
    file: UploadFile = File(None),
    query: str = Form(None),
    student_id: str = Header(None)
):
    #student_id = "66ab1c67c5484a224c5244ae"  # For now
    auth_token = request.headers.get("authorization")

    if not student_id or not auth_token:
        return {"error": "Missing student-id or Authorization token."}

    if file:
        query_text = transcribe_audio(file)
    elif query:
        query_text = query
    else:
        return {"error": "No query or file provided."}

    result = run_orchestrator(query_text, student_id)
    request_list = result.get("requestList", [])

    final_response_data = {}

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
                    "conceptTitle": title
                })

            else:
                print(f"📡 Calling combined API for: {title} [{dost_type}]")
                resp = requests.post("https://api.acadza.in/combined/create", json={"requestList": [req]})
                resp.raise_for_status()
                response_data = resp.json().get("data", {}).get(dost_type, {})

                if response_data:
                    dost_result = {}
                    if dost_type == "practiceTest":
                        dost_result = {
                            "practiceTestLink": response_data.get("testLink"),
                            "practiceTestTitle": response_data.get("testTitle", title)
                        }
                    elif dost_type == "practiceAssignment":
                        dost_result = {
                            "practiceAssignmentLink": response_data.get("assignmentLink"),
                            "practiceAssignmentTitle": response_data.get("assignmentTitle", title)
                        }
                    elif dost_type == "formula":
                        dost_result = {
                            "formulaLink": response_data.get("formulaLink"),
                            "formulaTitle": response_data.get("formulaTitle", title)
                        }
                    elif dost_type == "revision":
                        dost_result = {
                            "revisionLink": response_data.get("revisionLink"),
                            "revisionTitle": response_data.get("revisionTitle", title)
                        }
                    elif dost_type == "clickingPower":
                        dost_result = {
                            "clickingPowerLink": response_data.get("clickingLink"),
                            "clickingPowerTitle": response_data.get("clickingTitle", title)
                        }
                    elif dost_type == "pickingPower":
                        dost_result = {
                            "pickingPowerLink": response_data.get("pickingLink"),
                            "pickingPowerTitle": response_data.get("pickingTitle", title)
                        }
                    elif dost_type == "speedRace":
                        dost_result = {
                            "speedRaceLink": response_data.get("speedRaceLink"),
                            "speedRaceTitle": response_data.get("speedRaceTitle", title)
                        }

                    final_response_data.setdefault(dost_type, []).append(dost_result)

        except Exception as e:
            print(f"❌ API call failed for {dost_type}: {e}")

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
            "script": result.get("queryResponseText", ""),
            "analysis": result.get("queryAnalyzeText", ""),
            "tone": "motivated"
        }
    }

# -----------------------------
# 🧪 Run locally for testing
# -----------------------------
if __name__ == "__main__":
    uvicorn.run("FastAPI_App:app", host="0.0.0.0", port=10000, reload=True)
