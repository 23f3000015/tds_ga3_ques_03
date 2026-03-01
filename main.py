import os
import sys
import traceback
from io import StringIO
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google import genai
from google.genai import types

app = FastAPI()

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
# Tool Function
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
# AI Error Analysis
# -----------------------------

class ErrorAnalysis(BaseModel):
    error_lines: List[int]

def analyze_error_with_ai(code: str, tb: str) -> List[int]:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    prompt = f"""
Analyze the following Python code and traceback.
Return ONLY the line number(s) where the error occurred.

CODE:
{code}

TRACEBACK:
{tb}
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "error_lines": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.INTEGER),
                    )
                },
                required=["error_lines"],
            ),
        ),
    )

    result = ErrorAnalysis.model_validate_json(response.text)
    return result.error_lines


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

    # Only call AI if error occurs
    error_lines = analyze_error_with_ai(request.code, execution["output"])

    return {
        "error": error_lines,
        "result": execution["output"]
    }
