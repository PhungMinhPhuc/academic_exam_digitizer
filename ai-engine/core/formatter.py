import json
import re
from pathlib import Path


def json_to_raw_tex(json_path, output_input_tex_path):
    json_path = Path(json_path)
    output_input_tex_path = Path(output_input_tex_path)

    with open(json_path, "r", encoding="utf-8") as f:
        pages_data = json.load(f)

    raw_content = []
    for question in pages_data.get("questions", []):
        # raw_content.append(f"%Câu {question.get('id', 'N/A')}")
        # raw_content.append(question.get("latex_code", ""))
        # raw_content.append("\n")
        latex = question.get("latex_code", "")
        processed_latex = re.sub(r'\\n(?![a-zA-Z])', '\n', latex)
        # processed_latex = latex.replace("\\n", "\n")
        raw_content.append(processed_latex)
        # raw_content.append(latex)
        raw_content.append("\n")

    # Ghi nội dung thô ra file input.tex
    with open(output_input_tex_path, "w", encoding="utf-8") as f:
        f.write("\n".join(raw_content))
    
    return output_input_tex_path

def compile_main_pdf(sample_dir, main_tex_name="main.tex"):
    """
    Biên dịch file main.tex có sẵn trong thư mục.
    """
    main = Path(sample_dir)
    main_file = sample_dir / main_tex_name

    if not main_file.exists():
        print(f"Error: Không tìm thấy file {main_tex_name} tại {sample_dir}")
        return

    print(f"Compiling {main_tex_name}...")