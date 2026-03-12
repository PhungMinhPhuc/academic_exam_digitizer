import os
from dotenv import load_dotenv

# Initialization

# Load file .env
load_dotenv() 

API_KEY = os.getevn("API_KEY")
TEMPERATURE = 0 # Deterministic output, less randomness

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "exam_metadata": {
            "type": "object",
            "properties": {
                "grade": {"type": "string"},
                "subject": {
                    "type": "string",
                    "enum": [
                        "TO",  # Toán
                        "LY",  # Vật lý
                        "HO",  # Hóa học
                        "SI",  # Sinh học
                        "SU",  # Lịch sử
                        "DI",  # Địa lý
                        "AN"   # Tiếng Anh
                    ]
                },
                "total_questions": {"type": "integer"}
            }
        },
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "type": {"type": "string", "enum": ["multi_choice", "true_false", "short_answer", "essay"]},
                    "latex_code": {"type": "string"},
                    "explanation": {"type": "string"}
                },
                "required": ["id", "type", "latex_code"]  # explanation field is optional
            }
        }
    },
    "required": ["questions"]
}
