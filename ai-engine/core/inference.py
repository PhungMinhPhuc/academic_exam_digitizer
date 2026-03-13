from google import genai
from google.genai import types
import PIL.Image
from pathlib import Path
from .config import API_KEY, RESPONSE_SCHEMA, TEMPERATURE

# -----------------------------------
# Init client (global reuse)
# -----------------------------------

client = genai.Client(api_key=API_KEY)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "latex_rules.txt"

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    RULE_PROMPT = f.read()


def call_ai_vision(images_path, figure_manifest):

    # -------------------------------
    # 1. Prepare figure metadata
    # -------------------------------

    if figure_manifest:
        asset_info = "\n".join(
            [
                f"- Figure at {f['path']} (Vertical position: {f['vertical_position']:.2f})"
                for f in figure_manifest
            ]
        )
    else:
        asset_info = "No figures detected."

    # -------------------------------
    # 2. User prompt
    # -------------------------------

    user_prompt = f"""
    IMPORTANT:
    - Do NOT invent answers if they are not present in the source.

    Detected figures:
    {asset_info}

    Task:
    Convert the content of the images into LaTeX following the system rules.
    Return JSON strictly following the schema.
    """

    # -------------------------------
    # 3. Load images
    # -------------------------------

    all_image_files = []

    if isinstance(images_path, list):
        all_image_files.extend(images_path)
    else:
        all_image_files.append(images_path)

    if figure_manifest:
        for f in figure_manifest:
            all_image_files.append(f["path"])

    images = [PIL.Image.open(p) for p in all_image_files]

    # -------------------------------
    # 4. Call Gemini
    # -------------------------------

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=images + [user_prompt],
        config=types.GenerateContentConfig(
            temperature=TEMPERATURE,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            system_instruction=RULE_PROMPT
        )
    )

    return response.text