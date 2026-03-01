import sys
import traceback
import re
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
# Extract Error Line From Traceback
# -----------------------------
def extract_error_line(traceback_text: str) -> List[int]:
    matches = re.findall(r'line (\d+)', traceback_text)

    if matches:
        # Take last occurrence (actual error line)
        return [int(matches[-1])]

    return []


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

    error_lines = extract_error_line(execution["output"])

    return {
        "error": error_lines,
        "result": execution["output"]
    }


# -----------------------------
# Root Health Check
# -----------------------------
@app.get("/")
def home():
    return {"status": "running"}
