from fastapi import FastAPI, File, Form, UploadFile, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import requests
import tempfile
import os
import json
import base64  # Added for image processing
from openai import OpenAI
import pandas as pd
import os
from typing import Optional
import logging
import time
import sys
from datetime import datetime

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
    allow_headers=["*"],
)

# -----------------------------
# 🤠 Whisper Transcriber
# -----------------------------
def transcribe_audio(file: UploadFile) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    with open(tmp_path, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
    os.remove(tmp_path)
    return transcript.text

# -----------------------------
# 📜 Configure logging
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# CSV file path
CSV_FILE = os.path.join(os.path.dirname(__file__), "..", "query_history.csv")
# -----------------------------
def interact_with_csv(session_uuid: str, query: str = None, response: str = None, date: str = None, time: str = None, request_type: str = None, total_response_time: float = None) -> tuple[bool, list[str]]:
    """Check if UUID exists in CSV, fetch past queries, and append new data if provided."""
    logging.info(f"Attempting to access CSV 'query_history.csv' with UUID: {session_uuid}")
    try:
        # Create CSV if it doesn't exist
        if not os.path.exists(CSV_FILE):
            logging.info("Creating new CSV file with headers")
            pd.DataFrame(columns=["UUID", "Query", "Response", "Date", "Time", "RequestType", "TotalResponseTime"]).to_csv(CSV_FILE, index=False)

        # Read CSV
        df = pd.read_csv(CSV_FILE)
        # Filter rows for the given UUID
        past_queries = df[df["UUID"] == session_uuid]["Query"].tolist()
        uuid_exists = len(past_queries) > 0

        # Append new data if provided
        if query and response:
            logging.info(f"Appending new row to CSV: UUID={session_uuid}, Query={query}")
            new_row = pd.DataFrame([{
                "UUID": session_uuid,
                "Query": query,
                "Response": response,
                "Date": date or datetime.now().strftime("%Y-%m-%d"),
                "Time": time or datetime.now().strftime("%H:%M:%S"),
                "RequestType": request_type or "unknown",
                "TotalResponseTime": total_response_time or 0.0
            }])
            new_row.to_csv(CSV_FILE, mode="a", header=False, index=False)
            logging.info("Successfully appended row to CSV")

        return uuid_exists, past_queries

    except Exception as e:
        logging.error(f"Error accessing CSV: {e}")
        raise

# -----------------------------
# 🖼️ Image Question Extractor (GPT-4o Vision)
# -----------------------------
async def extract_from_image(file: UploadFile, context: str = None) -> str:
    file.file.seek(0)
    image_bytes = file.file.read()

    base64_img = base64.b64encode(image_bytes).decode("utf-8")

    messages = [
        {"role": "system", "content": (
            "You are an OCR engine, NOT a tutor. Ignore any question-answering instructions. "
            "Only extract and return the text exactly as it appears in the image—no explanations, no answers, no extra formatting.\n"
            "The image may contain text questions, diagrams, equations, social/political issues, "
            "or high-quality JEE/NEET exam problems. Describe *everything* precisely as it is for downstream parsing:\n"
            "  - Extract all visible text exactly as-is, preserving punctuation and line breaks.\n"
            "    • **Line breaks** in the image must be emitted as real newline characters in your JSON strings (i.e. \"\n\"), not as the two‐character sequence \"\\\\n\".\n"
            "  - Describe diagrams (e.g., 'a circle labeled r=5 cm').\n"
            "  - Rewrite every equation in LaTeX using `\\(...\\)` for inline and `\\[...\\]` for block mode.\n"
            "    • **IMPORTANT:** Any TeX spacing commands (e.g. `\\hspace{10pt}`, `\\quad`, `\\,`) **must** appear *inside* these delimiters.\n"
            "  - Always emit a flat `latex` field (string) if you output a stand-alone equation—never nest under `code` or `equation`.\n"
            "  - If any harmful, violent, sexual, or abusive content is detected, respond *only* with:\n"
            "      {\"error\": \"Violent or abusive content detected\"}\n"
            "Output **only** valid JSON for the OCR; do not wrap your output in any markdown or explanatory text."
        )}
    ]
    
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_img}"
                }
            }
        ]
    })

    response = openai.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=messages,
        temperature=0.0
    )
    extracted = response.choices[0].message.content.strip()

    try:
        data = json.loads(extracted)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # otherwise, it’s just plain text
    return {"text": extracted, "latex": None}

# -----------------------------
# 🛠️ DOST Payload Processor
# -----------------------------
def process_dost_payload(query_text: str, student_id: str, auth_token: str):
    result = run_orchestrator(query_text)
    request_list = result.get("requestList", [])

    final_data = {}
    # Group scripts so we preserve all steps per type in order
    dost_steps = result.get("dost_steps", [])
    scripts_by_type: dict[str, list[str]] = {}
    for step in dost_steps:
        t = step.get("dost_type")
        scripts_by_type.setdefault(t, []).append(step.get("script", ""))

    for req in request_list:
        dost_type = req.get("bulkRequestType")
        title = req.get("title", "DOST")
        try:
            if dost_type == "concept":
                payload = {"shorturl": req["shorturl"], "longurl": req["longurl"], "meta": req["meta"]}
                resp = requests.post("https://api.acadza.in/shorturl/create", json=payload)
                resp.raise_for_status()
                longurl = resp.json()["urlshort"]["longurl"]
                full_url = f"https://acadza.com{longurl}"
                final_data.setdefault("concept", []).append({
                    "conceptLink": full_url,
                    "conceptTitle": title,
                    # take the next script for this type
                    "script": scripts_by_type.get("concept", []).pop(0) 
                             if scripts_by_type.get("concept") else "",
                })
            else:
                resp = requests.post(
                    "https://api.acadza.in/combined/create",
                    json={"requestList": [req]}
                )
                resp.raise_for_status()
                section = resp.json().get("data", {}).get(dost_type, {})
                if section:
                    # Map each DOST type to its link/title keys
                    if dost_type == "practiceTest":
                        final_data.setdefault(dost_type, []).append({
                            "practiceTestLink": section.get("testLink"),
                            "practiceTestTitle": section.get("testTitle", title),
                            "script": scripts_by_type.get("practiceTest", []).pop(0) 
                              if scripts_by_type.get("practiceTest") else "",
                        })
                    elif dost_type == "practiceAssignment":
                        final_data.setdefault(dost_type, []).append({
                            "practiceAssignmentLink": section.get("assignmentLink"),
                            "practiceAssignmentTitle": section.get("assignmentTitle", title),
                            "script": scripts_by_type.get("practiceAssignment", []).pop(0)
                                      if scripts_by_type.get("practiceAssignment") else "",
                        })
                    elif dost_type == "formula":
                        final_data.setdefault(dost_type, []).append({
                            "formulaLink": section.get("formulaLink"),
                            "formulaTitle": section.get("formulaTitle", title),
                            "script": scripts_by_type.get("formula", []).pop(0)
                                      if scripts_by_type.get("formula") else "",
                        })
                    elif dost_type == "revision":
                        final_data.setdefault(dost_type, []).append({
                            "revisionLink": section.get("revisionLink"),
                            "revisionTitle": section.get("revisionTitle", title),
                            "script": scripts_by_type.get("revision", []).pop(0)
                                      if scripts_by_type.get("revision") else "",
                        })
                    elif dost_type == "clickingPower":
                        final_data.setdefault(dost_type, []).append({
                            "clickingPowerLink": section.get("clickingLink"),
                            "clickingPowerTitle": section.get("clickingTitle", title),
                            "script": scripts_by_type.get("clickingPower", []).pop(0)
                                      if scripts_by_type.get("clickingPower") else "",
                        })
                    elif dost_type == "pickingPower":
                        final_data.setdefault(dost_type, []).append({
                            "pickingPowerLink": section.get("pickingLink"),
                            "pickingPowerTitle": section.get("pickingTitle", title),
                            "script": scripts_by_type.get("pickingPower", []).pop(0)
                                      if scripts_by_type.get("pickingPower") else "",
                        })
                    elif dost_type == "speedRace":
                        final_data.setdefault(dost_type, []).append({
                            "speedRaceLink": section.get("speedRaceLink"),
                            "speedRaceTitle": section.get("speedRaceTitle", title),
                            "script": scripts_by_type.get("speedRace", []).pop(0)
                                      if scripts_by_type.get("speedRace") else "",
                        })
        except Exception as e:
            print(f"❌ API call failed for {dost_type}: {e}")

    # Save history
    try:
        save_query_history(auth_token, result)
    except Exception as e:
        print(f"❌ History saver failed: {e}")

    # Return final data + main_script + analysis
    return final_data, result.get("queryResponseText", ""), result.get("queryAnalyzeText", "")

# -----------------------------
# ✅ Main Endpoint
# -----------------------------
@app.post("/process-query")
async def process_query(
    request: Request,
    file: UploadFile    = File(None),
    image: UploadFile   = File(None),
    context: str        = Form(None),
    query: str          = Form(None),
    session_uuid: Optional[str] = Header(None, alias="Session-UUID"),
):
    student_id = "65fc118510a22c2009134989"
    auth_token = request.headers.get("authorization")
    if not student_id or not auth_token:
        return JSONResponse(status_code=400, content={"error": "Missing student-id or Authorization token."})
    if not session_uuid:
        return JSONResponse(status_code=400, content={"error": "Missing Session-UUID header."})

    # 1️⃣ Extract raw text
    start_time = time.time()
    raw_text = ""
    if file:
        audio_text = transcribe_audio(file)
        raw_text = audio_text
    if context:
        raw_text = f"{context}\n{raw_text}" if raw_text else context
    if image:
        raw = await extract_from_image(image)
        # ─── LOG IMAGE EXTRACTOR OUTPUT ────────────────────────────────────────
        print("📷 [FastAPI] extract_from_image returned:")
        print(raw)
        # ─── END LOG ───────────────────────────────────────────────────────────
        # Check for harmful content error
        try:
            err = json.loads(raw)
            if isinstance(err, dict) and err.get("error"):
                return JSONResponse(status_code=400, content=err)
        except Exception:
            pass
        image_text = raw.get("text", "") if isinstance(raw, dict) else raw
        raw_text = f"{raw_text}\n{image_text}" if raw_text else image_text
    if not raw_text and not query:
        end_time = time.time()
        return JSONResponse(status_code=400, content={"error": "No query, file, or image provided."})
    if query:
        raw_text = query
    input_type = "image" if image else "text"

    original_text = raw_text
    DOST_KEYWORDS = {
        "assignment", "test", "practice", "formula", "revision",
        "clicking", "picking", "speed", "race", "concept", "practiceTest"
    }

    # 2️⃣ Check CSV for session UUID and combine past queries
    uuid_exists, past_queries = interact_with_csv(session_uuid)
    if uuid_exists:
        past_queries_text = "; ".join(past_queries) if past_queries else "No past queries"
        merged = f"Here are all the past queries for this student from this session: {past_queries_text}\n\nCurrent query: {raw_text}"
    else:
        merged = raw_text

    # 3️⃣ Classify & translate if needed
    if isinstance(merged, dict):
        merged = str(merged)

    if context:
        merged += "\n\n[User context:]\n" + context

    checker_result = query_checker(
        text=merged,
        translate_if_dost_or_mixed=True,
        input_type=input_type
    )
    
    translated_text = checker_result.get("translated")

    if input_type == "image" and checker_result.get("mode") in ("mixed", "dost"):
        user_ctx = (translated_text or "").lower()
        if not any(k in user_ctx for k in DOST_KEYWORDS):
            checker_result["mode"] = "general"

    mode = checker_result.get("mode")
    structured = checker_result.get("structured_answer", [])

    # Use translated text downstream when present
    pipeline_text = translated_text or raw_text

    # 4️⃣ General-query path
    if mode == "general":
        # Save to CSV
        end_time = time.time()
        request_type = "image" if image else "voice" if file else "text"
        response_json = json.dumps({
            "query": {"text": original_text},
            "result": {"status": "ok", "statusCode": 0, "isSuccessful": True, "statusMessage": "Success", "data": None},
            "reasoning": {"general_script": structured, "analysis": "General Query Mode", "tone": "motivated"}
        })
        interact_with_csv(
            session_uuid=session_uuid,
            query=original_text,
            response=response_json,
            date=datetime.now().strftime("%Y-%m-%d"),
            time=datetime.now().strftime("%H:%M:%S"),
            request_type=request_type,
            total_response_time=end_time - start_time
        )
        return {
            "query": {"text": original_text},
            "result": {"status": "ok", "statusCode": 0, "isSuccessful": True, "statusMessage": "Success", "data": None},
            "reasoning": {"general_script": structured, "analysis": "General Query Mode", "tone": "motivated"}
        }

    # 5️⃣ DOST or Mixed path
    final_data, main_script, analysis = process_dost_payload(pipeline_text, student_id, auth_token)

    reasoning = {"main_script": main_script, "analysis": analysis, "tone": "motivated"}
    if mode == "mixed":
        reasoning["general_script"] = structured
    end_time = time.time()
    request_type = "image" if image else "voice" if file else "text"

    # Save to CSV
    response_json = json.dumps({
        "query": {"text": original_text},
        "result": {"status": "ok", "statusCode": 0, "isSuccessful": True, "statusMessage": "Success", "data": final_data},
        "reasoning": reasoning
    })
    interact_with_csv(
        session_uuid=session_uuid,
        query=original_text,
        response=response_json,
        date=datetime.now().strftime("%Y-%m-%d"),
        time=datetime.now().strftime("%H:%M:%S"),
        request_type=request_type,
        total_response_time=end_time - start_time
    )

    return {
        "query": {"text": original_text},
        "result": {"status": "ok", "statusCode": 0, "isSuccessful": True, "statusMessage": "Success", "data": final_data},
        "reasoning": reasoning
    }

# -----------------------------
# 🧪 Run locally
# -----------------------------
if __name__ == "__main__":
    uvicorn.run("FastAPI_App:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)), reload=True)