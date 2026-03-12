import os
from dotenv import load_dotenv

# Initialization

# Load file .env
load_dotenv() 

API_KEY = os.getenv("API_KEY")
TEMPERATURE = 0 # Deterministic output, less randomness

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "grade": {"type": "string"},
                    "type": {"type": "string", "enum": ["multi_choice", "true_false", "short_answer", "essay"]},
                    "latex_code": {"type": "string"},
                    "explanation": {"type": "string"}
                },
                "required": ["id", "subject", "grade", "type", "latex_code"]
            }
        }
    },
    "required": ["questions"]
}
