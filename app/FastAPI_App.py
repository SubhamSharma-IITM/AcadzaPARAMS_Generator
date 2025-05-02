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
            "Output **only** valid JSON or plain text for the OCR; do not wrap your output in any markdown or explanatory text."
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
        messages=messages,
        temperature=0.0
    )
    extracted = response.choices[0].message.content.strip()

    try:
        data = json.loads(extracted)
        if isinstance(data, dict) and data.get("error"):
            return extracted
    except json.JSONDecodeError:
        pass

    return extracted


# -----------------------------
# 🛠️ DOST Payload Processor
# -----------------------------
def process_dost_payload(query_text: str, student_id: str, auth_token: str):
    result = run_orchestrator(query_text)
    request_list = result.get("requestList", [])

    final_data = {}
    dost_steps = result.get("dost_steps", [])
    dost_step_map = {step.get("dost_type"): step.get("script", "") for step in dost_steps}

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
                    "script": dost_step_map.get("concept", ""),
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
                            "script": dost_step_map.get("practiceTest", ""),
                        })
                    elif dost_type == "practiceAssignment":
                        final_data.setdefault(dost_type, []).append({
                            "practiceAssignmentLink": section.get("assignmentLink"),
                            "practiceAssignmentTitle": section.get("assignmentTitle", title),
                            "script": dost_step_map.get("practiceAssignment", ""),
                        })
                    elif dost_type == "formula":
                        final_data.setdefault(dost_type, []).append({
                            "formulaLink": section.get("formulaLink"),
                            "formulaTitle": section.get("formulaTitle", title),
                            "script": dost_step_map.get("formula", ""),
                        })
                    elif dost_type == "revision":
                        final_data.setdefault(dost_type, []).append({
                            "revisionLink": section.get("revisionLink"),
                            "revisionTitle": section.get("revisionTitle", title),
                            "script": dost_step_map.get("revision", ""),
                        })
                    elif dost_type == "clickingPower":
                        final_data.setdefault(dost_type, []).append({
                            "clickingPowerLink": section.get("clickingLink"),
                            "clickingPowerTitle": section.get("clickingTitle", title),
                            "script": dost_step_map.get("clickingPower", ""),
                        })
                    elif dost_type == "pickingPower":
                        final_data.setdefault(dost_type, []).append({
                            "pickingPowerLink": section.get("pickingLink"),
                            "pickingPowerTitle": section.get("pickingTitle", title),
                            "script": dost_step_map.get("pickingPower", ""),
                        })
                    elif dost_type == "speedRace":
                        final_data.setdefault(dost_type, []).append({
                            "speedRaceLink": section.get("speedRaceLink"),
                            "speedRaceTitle": section.get("speedRaceTitle", title),
                            "script": dost_step_map.get("speedRace", ""),
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
):
    student_id = "65fc118510a22c2009134989"
    auth_token = request.headers.get("authorization")
    if not student_id or not auth_token:
        return JSONResponse(status_code=400, content={"error": "Missing student-id or Authorization token."})

    # 1️⃣ Extract raw text
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
        raw_text = raw
        input_type = "image"
         # ─── LOG WHAT WE PASS TO QUERY_CHECKER ────────────────────────────────
        print("🔍 [FastAPI] About to call query_checker with:")
        print("    raw_text   =", raw_text)
        print("    input_type =", input_type)
        # ─── END LOG ───────────────────────────────────────────────────────────
    elif file:
        raw_text = transcribe_audio(file)
        input_type = "text"
    elif query:
        raw_text = query
        input_type = "text"
    else:
        return JSONResponse(status_code=400, content={"error": "No query, file, or image provided."})

    original_text = raw_text
    DOST_KEYWORDS = {
    "assignment", "test", "practice", "formula", "revision",
    "clicking", "picking", "speed", "race", "concept"
}
    # 2️⃣ Classify & translate if needed
    merged = raw_text
    if context:
       merged += "\n\n[User context:]\n" + context

    checker_result = query_checker(
       text=merged,
        translate_if_dost_or_mixed=True,
        input_type=input_type
   )
    
    if input_type=="image" and checker_result.get("mode")in("mixed,dost"):
        user_ctx = (context or "").lower()
        if not any(k in user_ctx for k in DOST_KEYWORDS):
                checker_result["mode"]="general"

    mode            = checker_result.get("mode")
    structured      = checker_result.get("structured_answer", [])
    translated_text = checker_result.get("translated")

    # Use translated text downstream when present
    pipeline_text = translated_text or raw_text

    # 3️⃣ General-query path
    if mode == "general":
        return {
            "query": original_text,
            "result": {"status": "ok", "statusCode": 0, "isSuccessful": True, "statusMessage": "Success", "data": None},
            "reasoning": {"general_script": structured, "analysis": "General Query Mode", "tone": "motivated"}
        }

    # 4️⃣ DOST or Mixed path
    final_data, main_script, analysis = process_dost_payload(pipeline_text, student_id, auth_token)

    reasoning = {"main_script": main_script, "analysis": analysis, "tone": "motivated"}
    if mode == "mixed":
        reasoning["general_script"] = structured

    return {
        "query": original_text,
        "result": {"status": "ok", "statusCode": 0, "isSuccessful": True, "statusMessage": "Success", "data": final_data},
        "reasoning": reasoning
    }

# -----------------------------
# 🧪 Run locally
# -----------------------------
if __name__ == "__main__":
    uvicorn.run("FastAPI_App:app", host="0.0.0.0", port=10000, reload=True)
