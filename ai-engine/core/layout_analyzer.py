from ultralytics import YOLO
import pymupdf
from PIL import Image
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "yolo26l-doclaynet.pt"

class DocLayoutEngine:
    # Initalization
    def __init__(self, model_path='yolo26l-doclaynet.pt'):
        # Load DocLayout-YOLO model (requires local .pt weights)
        self.model = YOLO(MODEL_PATH)

    # Analyze and crop
    def analyze_and_crop(self, PDF_PATH, output_dir):
        doc = pymupdf.open(PDF_PATH)
        figure_coords = []

        for page_idx, page in enumerate(doc):
            # Render page to image
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2)) # (x scale, y scale)
            img_path = f"page_{page_idx}.png"
            pix.save(img_path)

            # Run DocLayout_YOLO
            results = self.model.predict(img_path, conf=0.25) # confidence threshold

            img = Image.open(img_path)
            # Loop through each detected bounding box from YOLO
            for i, box in enumerate(results[0].boxes):
                # Get  the class index of the detected object
                cls = int(box.cls[0])
                # Convert the class index to the actual label name
                label = results[0].names[cls]

                # Nếu là Figure 
                if label.lower() == 'figure':
                    coords = box.xyxy[0].tolist() # [x1, y1, x2, y2]
                    crop_img = img.crop((coords[0], coords[1], coords[2], coords[3]))
                    crop_path = f"{output_dir}/fig_{page_idx}_{i}.png"
                    crop_img.save(crop_path)
                    figure_coords.append({"path": crop_path, "page": page_idx})
        return figure_coords