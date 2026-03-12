import pymupdf
import os

OUTPUT = "figure_folder"
pdf_path = "E:\Downloads\Visionary_Solutions_for_Academic_Digitization\Test_sample\Test_T_2018.pdf"

def img_extraction(PDF_PATH):
    if not os.path.exists(OUTPUT): os.makedirs(OUTPUT)
    doc = pymupdf.open(PDF_PATH)
    figCount = 0
    for page in doc:
        for img in page.get_images():
            # cross reference - get image ID in the pdf file
            xref = img[0]
            # convert the image object to proccessable image data
            pix = pymupdf.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3: pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            pix.save(os.path.join(OUTPUT, f"figure_{figCount + 1}.png"))
            figCount += 1
    return figCount

if __name__ == "__main__":
    img_extraction(pdf_path)
