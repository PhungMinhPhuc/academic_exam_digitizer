import pymupdf
import os

OUTPUT = "figure_folder"

def imgExtraction(PDF_PATH, prompt):
    if not os.path.exists(OUTPUT): os.makedirs(OUTPUT)
    doc = pymupdf.open(PDF_PATH)
    fig_count = 0
    for page in doc:
        # from  in page.get_images()

    
# def extract_images():
# if not os.path.exists(IMAGE_FOLDER): os.makedirs(IMAGE_FOLDER)
# doc = fitz.open(PDF_PATH)
# img_count = 0
# for page in doc:
#     for img in page.get_images():
#         xref = img[0]
#         pix = fitz.Pixmap(doc, xref)
#         if pix.n - pix.alpha > 3: pix = fitz.Pixmap(fitz.csRGB, pix)
#         pix.save(os.path.join(IMAGE_FOLDER, f"figure_{img_count+1}.png"))
#         img_count += 1
# return img_count
