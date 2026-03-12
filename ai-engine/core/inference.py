import google.generativeai as genai
import PIL.Image
from .config import API_KEY, RESPONSE_SCHEMA, TEMPERATURE
from pathlib import Path
import json

# Initialization
genai.configure(api_key=API_KEY)
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "latex_rules.txt"

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    RULE_PROMPT = f.read()

# Khởi tạo model ngoài hàm để tái sử dụng
_MODEL_CACHE = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": RESPONSE_SCHEMA,
        "temperature": TEMPERATURE,
    },
    system_instruction=RULE_PROMPT
)

def call_ai_vision(images_path, figure_manifest):
    global _MODEL_CACHE
    
    if figure_manifest:
        asset_info = "\n".join(
            [f"- {f['path']} at vertical position {f['vertical_position']:.2f}"
             for f in figure_manifest]
        )
    else:
        asset_info = "No figures detected."

    # Prompt
    user_prompt = f"""
    Detected figures (metadata):
    {asset_info}

    Task: Convert the provided image content to LaTeX following the system instructions.
    """

    images = [PIL.Image.open(p) for p in images_path]

    response = _MODEL_CACHE.generate_content(
        images + [user_prompt]
    )

    return response.text