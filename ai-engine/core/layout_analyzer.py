from ultralytics import YOLO
import pymupdf
from PIL import Image
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "yolo26l-doclaynet.pt"

class DocLayoutEngine:
    # Initalization
    def __init__(self):
        # Load DocLayout-YOLO model (requires local .pt weights)
        self.model = YOLO(MODEL_PATH)

    # Analyze and crop IMG
    def analyze_and_crop_img(self, IMG_PATH, output_dir, page_idx, figure_coords):

        # Tạo thư mục 'extracted_figures' nằm cùng cấp với file IMG_PATH
        save_dir = Path(output_dir) / "extracted_figures"
        save_dir.mkdir(parents=True, exist_ok=True) # Tự động tạo thư mục nếu chưa có

        # Run DocLayout_YOLO
        results = self.model.predict(IMG_PATH, conf=0.25) # confidence threshold

        img = Image.open(IMG_PATH)
        img_width, img_height = img.size
        # Loop through each detected bounding box from YOLO
        for i, box in enumerate(results[0].boxes):
            # Get  the class index of the detected object
            cls = int(box.cls[0])
            # Convert the class index to the actual label name
            label = results[0].names[cls]

            # Nếu là Figure 
            if label.lower() == 'figure':
                coords = box.xyxy[0].tolist() # [x1, y1, x2, y2]
                # Tính toán vị trí tương đối (ví dụ: ảnh nằm ở 1/3 trên của trang)
                relative_y = coords[1] / img_height
                crop_img = img.crop((coords[0], coords[1], coords[2], coords[3]))
                crop_path = save_dir / f"fig_p{page_idx}_{i}.png"
                crop_img.save(str(crop_path))
                figure_coords.append({
                    "path": crop_path,
                    "page": page_idx,
                    "bbox": coords,
                    "vertical_position": relative_y # Chỉ số để neo vào câu hỏi
                })
        return figure_coords


    def process_layout_engine(self, FILE_PATH, output_dir):
        is_pdf = FILE_PATH.lower().endswith(".pdf")
        figure_coords = []
        page_images = []

        if is_pdf:
            doc = pymupdf.open(FILE_PATH)
            for page_idx, page in enumerate(doc):
                # Render page to image
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2)) # (x scale, y scale)
                img_dir = Path(output_dir) / "pages"
                img_dir.mkdir(parents=True, exist_ok=True)
                img_path = img_dir / f"page_{page_idx}.png"
                pix.save(str(img_path))
                page_images.append(img_path)
                self.analyze_and_crop_img(img_path, output_dir, page_idx, figure_coords)
        else:
            self.analyze_and_crop_img(FILE_PATH, output_dir, 0, figure_coords)
        return page_images, figure_coords



    #     # Analyze and crop PDF
    # def analyze_and_crop_pdf(self, FILE_PATH, output_dir):
    #     doc = pymupdf.open(FILE_PATH)
    #     figure_coords = []

    #     for page_idx, page in enumerate(doc):
    #         # Render page to image
    #         pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2)) # (x scale, y scale)
    #         img_path = f"page_{page_idx}.png"
    #         pix.save(img_path)

    #         # Run DocLayout_YOLO
    #         results = self.model.predict(img_path, conf=0.25) # confidence threshold

    #         img = Image.open(img_path)
    #         img_width, img_height = img.size
    #         # Loop through each detected bounding box from YOLO
    #         for i, box in enumerate(results[0].boxes):
    #             # Get  the class index of the detected object
    #             cls = int(box.cls[0])
    #             # Convert the class index to the actual label name
    #             label = results[0].names[cls]

    #             # Nếu là Figure 
    #             if label.lower() == 'figure':
    #                 coords = box.xyxy[0].tolist() # [x1, y1, x2, y2]
    #                 # Tính toán vị trí tương đối (ví dụ: ảnh nằm ở 1/3 trên của trang)
    #                 relative_y = coords[1] / img_height
    #                 crop_img = img.crop((coords[0], coords[1], coords[2], coords[3]))
    #                 crop_path = f"{output_dir}/fig_{page_idx}_{i}.png"
    #                 crop_img.save(crop_path)
    #                 figure_coords.append({
    #                     "path": crop_path,
    #                     "page": page_idx,
    #                     "bbox": coords,
    #                     "vertical_position": relative_y # Chỉ số để neo vào câu hỏi
    #                 })
    #     return figure_coords