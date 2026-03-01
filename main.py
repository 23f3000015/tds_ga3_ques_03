import os
import sys
import traceback
import requests
from io import StringIO
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# -----------------------------
# Enable CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Models
# -----------------------------
class CodeRequest(BaseModel):
    code: str

class CodeResponse(BaseModel):
    error: List[int]
    result: str


# -----------------------------
# Execute Python Code
# -----------------------------
def execute_python_code(code: str) -> dict:
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code)
        output = sys.stdout.getvalue()
        return {"success": True, "output": output}

    except Exception:
        output = traceback.format_exc()
        return {"success": False, "output": output}

    finally:
        sys.stdout = old_stdout


# -----------------------------
# AI Error Analysis (AI Pipe Gemini)
# -----------------------------
def analyze_error_with_ai(code: str, tb: str) -> List[int]:

    prompt = f"""
Analyze the following Python code and traceback.
Return ONLY the line number(s) where the error occurred.

Respond strictly in this JSON format:
{{ "error_lines": [line_numbers] }}

CODE:
{code}

TRACEBACK:
{tb}
"""

    response = requests.post(
        "https://aipipe.org/geminiv1beta/models/gemini-1.5-flash:generateContent",
        headers={
            "Authorization": f"Bearer {os.getenv('AI_PIPE_TOKEN')}",
            "Content-Type": "application/json"
        },
        json={
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
    )

    data = response.json()

    try:
        # Extract AI text response
        ai_text = data["candidates"][0]["content"]["parts"][0]["text"]

        import json
        parsed = json.loads(ai_text)

        return parsed.get("error_lines", [])

    except Exception:
        return []


# -----------------------------
# Endpoint
# -----------------------------
@app.post("/code-interpreter", response_model=CodeResponse)
def code_interpreter(request: CodeRequest):

    execution = execute_python_code(request.code)

    if execution["success"]:
        return {
            "error": [],
            "result": execution["output"]
        }

    error_lines = analyze_error_with_ai(request.code, execution["output"])

    return {
        "error": error_lines,
        "result": execution["output"]
    }
