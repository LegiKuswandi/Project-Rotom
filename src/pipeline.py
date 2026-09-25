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
        
        gray_corrected = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY) if len(corrected.shape) == 3 else corrected
        
        # Percobaan OCR Pertama (Posisi Normal)
        raw_text, confidence = self.ocr.extract_text(gray_corrected)
        fields = self.parser.parse(raw_text)
        rotation_angle = 0.0

        # Fallback Cerdas: Jika kartu terbalik (email & phone N/A), putar 180 derajat
        if fields["email"] == "N/A" and fields["phone"] == "N/A":
            gray_rotated = cv2.rotate(gray_corrected, cv2.ROTATE_180)
            raw_text_rot, conf_rot = self.ocr.extract_text(gray_rotated)
            fields_rot = self.parser.parse(raw_text_rot)
            
            # Gunakan hasil rotasi jika berhasil menemukan kontak
            if fields_rot["email"] != "N/A" or fields_rot["phone"] != "N/A":
                fields = fields_rot
                confidence = conf_rot
                rotation_angle = 180.0
                corrected = cv2.rotate(corrected, cv2.ROTATE_180)
                enhanced = cv2.rotate(enhanced, cv2.ROTATE_180)

        proc_time = int((time.time() - start_time) * 1000)
        
        metadata = {
            "document_detected": True,
            "rotation_angle": rotation_angle,
            "processing_time_ms": proc_time,
            "ocr_confidence": confidence,
            "image_width": w,
            "image_height": h,
            "fields": fields
        }
        
        return metadata, debug_img, corrected, enhanced