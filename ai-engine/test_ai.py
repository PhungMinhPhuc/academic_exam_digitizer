import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Khởi tạo
load_dotenv()
genai.configure(api_key=os.getenv("API_KEY"))

# 2. Đường dẫn đến file cần thao tác
# Thay tên file path ở đây
PDF_PATH = "E:\Downloads\Visionary_Solutions_for_Academic_Digitization\Test_sample\Test_T_2018.pdf" 

def process_exam():
    # Upload file PDF lên hệ thống tạm thời của Google
    print(f"File uploading: {PDF_PATH}...")
    sample_file = genai.upload_file(path=PDF_PATH, display_name="Exam_Paper")

    # Cấu hình Model
    model = genai.GenerativeModel(model_name="gemini-3-flash-preview")

    # Prompt - Định nghĩa mọi quy tắc extest
    PROMPT = """
    Role: Expert Academic LaTeX Engineer specializing in the 'extest' package.
    Task: Convert exam content into high-fidelity LaTeX code.

    Strict Rules for 'extest' format:
    1. Every question starts with '% Câu n' and environment '\\begin{ex} ... \\end{ex}'.
    2. Math Mode: Use $...$ for ALL numbers, units, and coordinates.
    3. Decimals: Use Vietnamese format with curly braces for commas (e.g., $1{,}5$).
    4. Question Types:
    - Multiple Choice: Use \\choice{A}{B}{C}{D}. Mark correct with \\True.
    - True/False: Use \\choiceTF{...}{...}{...}{...}. Mark correct with \\True.
    - Short Answer: Use \\shortans{result}.
    5. Solutions (\\loigiai):
    - For choiceTF: Always provide exactly 4 \\itemch commands inside \\begin{itemchoice} ... \\end{itemchoice}.
    - For grouped questions: Use \\sochc{n}{...} and \\begin{chc} ... \\end{chc}.
    6. Output: Strictly return a JSON object with keys: 'id', 'type', 'raw_latex'.
            "TO",  # Toán
        "LY",  # Vật lý
        "HO",  # Hóa học
        "SI",  # Sinh học
        "SU",  # Lịch sử
        "DI",  # Địa lý
        "AN"   # Tiếng Anh
    """

    print("Processing...")
    response = model.generate_content(
        [sample_file, PROMPT],
        generation_config={"response_mime_type": "application/json"}
    )

    # Lấy kết quả và lưu thành file json trên máy tính
    output_data = json.loads(response.text)
    
    # Đặt tên file đầu ra
    output_filename = "ket_qua_so_hoa.json"
    
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"Đã lưu kết quả vào file: {os.path.abspath(output_filename)}")

if __name__ == "__main__":
    process_exam()