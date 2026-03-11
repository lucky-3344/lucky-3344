import fitz
from paddleocr import PaddleOCR
import os
import glob

# Suppress Paddle logs
import logging
logging.getLogger("ppocr").setLevel(logging.WARNING)

def test_ocr_position(pdf_path):
    print(f"Processing {pdf_path}...")
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Render page to image
    zoom = 2.0 # 2x resolution (144 dpi)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    temp_img = "temp_page_ocr.png"
    pix.save(temp_img)
    print(f"Saved image {temp_img}, size: {os.path.getsize(temp_img)}")
    
    # Initialize OCR
    ocr = PaddleOCR(use_angle_cls=False, lang="ch", show_log=False)
    
    try:
        result = ocr.ocr(temp_img, cls=False)
        print(f"Raw OCR Result: {result}")
    except Exception as e:
        print(f"OCR Failed: {e}")
        return
    
    found = False
    print("--- OCR RESULTS ---")
    if result and result[0]:
        for line in result[0]:
            # line = [ [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], (text, confidence) ]
            box = line[0]
            text = line[1][0]
            print(f"Text: {text} | Box: {box}")
            
            clean_text = text.replace(" ", "")
            if "工程名称" in clean_text:
                print(f"--> MATCH FOUND: '{text}' at {box}")
                
                # Convert to PDF coordinates
                # Box[0] is Top-Left (x, y)
                # Box[2] is Bottom-Right (x, y)
                x0_px, y0_px = box[0]
                x1_px, y1_px = box[2]
                
                x0 = x0_px / zoom
                y0 = y0_px / zoom
                x1 = x1_px / zoom
                y1 = y1_px / zoom
                
                pdf_rect = fitz.Rect(x0, y0, x1, y1)
                print(f"Mapped PDF Rect: {pdf_rect}")
                
                # Check directly on PDF what is there (should be nothing)
                print(f"Text under rect: '{page.get_text(clip=pdf_rect)}'")
                
                found = True
                
                # Now lets try to draw a red box there to verify visually
                page.draw_rect(pdf_rect, color=(1, 0, 0), width=2)
                doc.save("test_ocr_marked.pdf")
                print("Saved marked PDF to test_ocr_marked.pdf")
                break
    
    if not found:
        print("Text '工程名称' not found by OCR.")
    
    doc.close()
    if os.path.exists(temp_img):
        os.remove(temp_img)

if __name__ == "__main__":
    folder = r"C:\Users\lucky\Desktop\test\替换工程名称"
    files = glob.glob(os.path.join(folder, "*.pdf"))
    if files:
        test_ocr_position(files[0])
