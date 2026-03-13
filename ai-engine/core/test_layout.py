from layout_analyzer import DocLayoutEngine


def main():
    FILE_PATH = "E:\Downloads\Visionary_Solutions_for_Academic_Digitization\Test_sample\Test_T_2024.jpg" 
    OUTPUT_DIR = "extracted_images"

    # Khởi tạo engine
    engine = DocLayoutEngine()

    # Chạy layout analysis
    page_images, figure_coords = engine.process_layout_engine(FILE_PATH, OUTPUT_DIR)

    # print("Pages extracted:", page_images)
    # print("Figures detected:", figure_coords)


if __name__ == "__main__":
    main()