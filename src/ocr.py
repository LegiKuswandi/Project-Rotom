import os
import pytesseract
import numpy as np

class OCREngine:
    def __init__(self, tesseract_cmd=None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        else:
            # Auto-detect path Tesseract di Windows jika terpasang di lokasi standar
            default_win_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(default_win_path):
                pytesseract.pytesseract.tesseract_cmd = default_win_path

    def extract_text(self, image: np.ndarray):
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            raw_text = pytesseract.image_to_string(image, config='--psm 3')
            
            confidences = [int(conf) for conf in data['conf'] if str(conf).isdigit() and int(conf) > 0]
            avg_confidence = round(float(np.mean(confidences)) / 100.0, 2) if confidences else 0.0
            
            return raw_text.strip(), avg_confidence
        except Exception as e:
            print(f"[OCR Error] {e}")
            return "", 0.0