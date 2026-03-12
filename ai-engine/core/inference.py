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
    model_name="gemini-3-flash",
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": RESPONSE_SCHEMA,
        "temperature": TEMPERATURE,
    },
    system_instruction=RULE_PROMPT
)

def call_ai_vision(file_path, figure_manifest):
    global _MODEL_CACHE
    
    if figure_manifest:
        asset_info = "\n".join(
            [f"- {f['path']} at vertical position {f['vertical_position']:.2f}"
             for f in figure_manifest]
        )
    else:
        asset_info = "No figures detected."

    # Prompt ngắn gọn vì các quy tắc đã nằm trong system_instruction
    user_prompt = f"""
    Detected figures (metadata):
    {asset_info}

    Task: Convert the provided image content to LaTeX following the system instructions.
    """

    try:
        # Đọc ảnh trực tiếp bằng PIL (Nhanh hơn upload_file)
        img = PIL.Image.open(file_path)

        # Gửi request
        response = _MODEL_CACHE.generate_content([img, user_prompt])

        # Kiểm tra phản hồi an toàn
        if not response.candidates or not response.candidates[0].content.parts:
            print("No content generated.")
            return None

        result_text = response.text
        
        # Mặc dù đã set response_mime_type nhưng đôi khi vẫn cần làm sạch
        result_text = result_text.strip()
        if result_text.startswith("```json"):
            result_text = result_text.strip("```json").strip("```")

        return result_text

    except Exception as e:
        print(f"Error with file {file_path}: {e}")
        return None