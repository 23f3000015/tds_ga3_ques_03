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
# Request / Response Models
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
# AI Error Analysis using IITM AI Pipe
# -----------------------------
def analyze_error_with_ai(code: str, tb: str) -> List[int]:

    prompt = f"""
Analyze the following Python code and traceback.
Identify ONLY the line number(s) where the error occurred.

Return strictly in this JSON format:
{{
  "error_lines": [line_numbers]
}}

CODE:
{code}

TRACEBACK:
{tb}
"""

    response = requests.post(
        "https://aipipe.iitm.ac.in/generate",
        headers={
            "Authorization": f"Bearer {os.getenv('AI_PIPE_TOKEN')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gemini-2.0-flash-exp",
            "prompt": prompt
        }
    )

    data = response.json()

    return data.get("error_lines", [])


# -----------------------------
# API Endpoint
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
