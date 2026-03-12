import os
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.layout_analyzer import DocLayoutEngine
from core.inference import call_ai_vision


MAX_WORKERS = 10
BATCH_SIZE = 3

def run_ai(input_path):

    input_file = Path(input_path)
    output_folder = Path("extracted_images")
    result_file = Path("ket_qua_so_hoa.json")

    if not input_file.exists():
        print(f"Error: File {input_path} does not exist.")
        return

    # ---------------------------------------
    # 1. Layout analysis (YOLO + PyMuPDF)
    # ---------------------------------------

    analyzer = DocLayoutEngine()

    page_images, figure_manifest = analyzer.process_layout_engine(
        str(input_file),
        str(output_folder)
    )

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
                    # Làm sạch markdown nếu AI trả về kèm thẻ ```json
                    clean_result = result.strip().replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(clean_result)

                    # KIỂM TRA: Nếu AI trả về 1 dict thay vì list
                    if isinstance(parsed, list):
                        for i, page_data in enumerate(parsed):
                            page_number = batch_idx * BATCH_SIZE + i
                            all_responses[page_number] = page_data
                    else:
                        # Nếu là dict, coi như dữ liệu của trang đầu tiên trong batch
                        page_number = batch_idx * BATCH_SIZE
                        all_responses[page_number] = parsed
                    print(f"Finished batch {batch_idx}")
            except Exception as e:
                print(f"Error batch {batch_idx}: {e}")

    # ---------------------------------------
    # 4. Order pages correctly
    # ---------------------------------------

    ordered_pages = [
        all_responses[k]
        for k in sorted(all_responses.keys())
    ]

    # ---------------------------------------
    # 5. Save JSON result
    # ---------------------------------------

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(
            ordered_pages,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(f"\nDigitization Finished!")
    print(f"Result saved to: {result_file}")

    # ---------------------------------------
    # 6. Optional cleanup
    # ---------------------------------------

    # print("Cleaning up page images...")
    # for img_path in page_images:
    #     if os.path.exists(img_path):
    #         os.remove(img_path)


if __name__ == "__main__":
    TEST_FILE = Path("E:\Downloads\Visionary_Solutions_for_Academic_Digitization\Test_sample\Test_T_2018.pdf")
    run_ai(TEST_FILE)


    