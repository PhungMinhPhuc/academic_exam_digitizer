import os
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.layout_analyzer import DocLayoutEngine
from core.inference import call_ai_vision
from core.formatter import json_to_raw_tex, compile_main_pdf


MAX_WORKERS = 5
BATCH_SIZE = 3

def run_ai(input_path):

    input_file = Path(input_path)
    BASE_DIR = Path(input_path).resolve().parent
    IMAGE_DIR = BASE_DIR / "extracted_images"
    result_file = BASE_DIR / "ket_qua_so_hoa.json"

    if not input_file.exists():
        print(f"Error: File {input_path} does not exist.")
        return

    # ---------------------------------------
    # 1. Layout analysis (YOLO + PyMuPDF)
    # ---------------------------------------

    analyzer = DocLayoutEngine()

    page_images, figure_manifest = analyzer.process_layout_engine(str(input_file), str(IMAGE_DIR))

    if not page_images:
        print("Error: Cannot render pages.")
        return

    print(f"Total pages: {len(page_images)}")

    # ---------------------------------------
    # 2. 
    # ---------------------------------------

    # chia pages thành batch
    batches = [
        page_images[i:i+BATCH_SIZE]
        for i in range(0, len(page_images), BATCH_SIZE)
    ]

    # ---------------------------------------
    # 3. AI Inference (parallel)
    # ---------------------------------------

    all_responses = {}
    final_questions = []
    results_map = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for batch_idx, batch in enumerate(batches):
            # figure thuộc batch này
            batch_figures = [
                f for f in figure_manifest
                if batch_idx * BATCH_SIZE <= f["page"] < batch_idx * BATCH_SIZE + len(batch)
            ]
            future = executor.submit(
                call_ai_vision,
                batch,
                batch_figures
            )

            futures[future] = batch_idx

        for future in as_completed(futures):

            batch_idx = futures[future]

            try:
                result = future.result()
                if result:
                    # Làm sạch JSON
                    clean_result = result.strip().replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(clean_result)

                    # Lấy đúng danh sách câu hỏi theo Schema
                    if isinstance(parsed, dict) and "questions" in parsed:
                        results_map[batch_idx] = parsed["questions"]
                    else:
                        results_map[batch_idx] = [] # Hoặc xử lý nếu AI trả về list trực tiếp
            except Exception as e:
                print(f"Error batch {batch_idx}: {e}")

    # ---------------------------------------
    # 4. Order pages correctly
    # ---------------------------------------

    for k in sorted(results_map.keys()):
        final_questions.extend(results_map[k])

    final_output = {"questions": final_questions}

    # ---------------------------------------
    # 5. Save JSON result
    # ---------------------------------------
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)
    print(f"\nDigitization Finished!")
    print(f"Result saved to: {result_file}")


    # ---------------------------------------
    # 6. Optional cleanup
    # ---------------------------------------

    # print("Cleaning up page images...")
    # for img_path in page_images:
    #     if os.path.exists(img_path):
    #         os.remove(img_path)

    JSON_OUTPUT = BASE_DIR / "ket_qua_so_hoa.json"
    INPUT_TEX = BASE_DIR / "input.tex" # File nội dung thô
    json_to_raw_tex(JSON_OUTPUT, INPUT_TEX)
        
    compile_main_pdf(BASE_DIR, "main.tex")

if __name__ == "__main__":
    TEST_FILE = Path("E:/Downloads/Visionary_Solutions_for_Academic_Digitization/Test_sample/T_TK_2024_p1.png")
    run_ai(TEST_FILE)
