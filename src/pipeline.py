import time
import cv2
import numpy as np

from src.detector import DocumentDetector
from src.perspective import PerspectiveCorrector
from src.enhancement import ImageEnhancer
from src.ocr import OCREngine
from src.parser import BusinessCardParser

class SmartScannerPipeline:
    def __init__(self):
        self.detector = DocumentDetector()
        self.corrector = PerspectiveCorrector()
        self.enhancer = ImageEnhancer()
        self.ocr = OCREngine()
        self.parser = BusinessCardParser()

    def process(self, image_path: str):
        start_time = time.time()
        image = cv2.imread(image_path)
        
        if image is None:
            return {
                "error": f"Failed to load image from path: {image_path}",
                "document_detected": False
            }, None, None, None

        h, w = image.shape[:2]
        is_detected, corners, debug_img = self.detector.detect(image)
        
        if not is_detected:
            proc_time = int((time.time() - start_time) * 1000)
            metadata = {
                "document_detected": False,
                "rotation_angle": 0.0,
                "processing_time_ms": proc_time,
                "ocr_confidence": 0.0,
                "image_width": w,
                "image_height": h,
                "fields": {
                    "name": "N/A",
                    "company": "N/A",
                    "email": "N/A",
                    "phone": "N/A"
                }
            }
            return metadata, debug_img, image, image

        corrected = self.corrector.transform(image, corners)
        enhanced = self.enhancer.enhance(corrected)
        
        # Menggunakan citra grayscale dari hasil pelurusan perspektif untuk OCR yang lebih jernih
        gray_corrected = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY) if len(corrected.shape) == 3 else corrected
        raw_text, confidence = self.ocr.extract_text(gray_corrected)
        
        fields = self.parser.parse(raw_text)
        proc_time = int((time.time() - start_time) * 1000)
        
        metadata = {
            "document_detected": True,
            "rotation_angle": 0.0,
            "processing_time_ms": proc_time,
            "ocr_confidence": confidence,
            "image_width": w,
            "image_height": h,
            "fields": fields
        }
        
        return metadata, debug_img, corrected, enhanced