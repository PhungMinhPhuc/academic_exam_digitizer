import pymupdf
import os

OUTPUT = "figure_folder"
pdf_path = "E:\Downloads\Visionary_Solutions_for_Academic_Digitization\Test_sample\Test_T_2018.pdf"

def imgExtraction(PDF_PATH):
    if not os.path.exists(OUTPUT): os.makedirs(OUTPUT)
    doc = pymupdf.open(PDF_PATH)
    figCount = 0
    for page in doc:
        for img in page.get_images():
            xref = img[0] # cross reference - get image ID in the pdf file
            pix = pymupdf.Pixmap(doc, xref) # convert the image object to proccessable image data
            if pix.n - pix.alpha > 3: pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            pix.save(os.path.join(OUTPUT, f"figure_{figCount + 1}.png"))
            figCount += 1
    return figCount

if __name__ == "__main__":
    imgExtraction(pdf_path)


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
