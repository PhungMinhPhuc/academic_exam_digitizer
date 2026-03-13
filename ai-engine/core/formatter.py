import json
import subprocess
from pathlib import Path

def json_to_tex(json_path, output_tex_path):
    with open(json_path, "r", encoding="utf-8") as f:
        pages_data = json.load(f)