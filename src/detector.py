import cv2
import numpy as np

class DocumentDetector:
    def __init__(self, min_area_ratio=0.08):
        self.min_area_ratio = min_area_ratio

    def detect(self, image: np.ndarray):
        h, w = image.shape[:2]
        image_area = h * w
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        canny = cv2.Canny(blurred, 50, 150)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(canny, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        doc_contour = None
        corners = None
        
        for c in contours:
            area = cv2.contourArea(c)
            if area < (image_area * self.min_area_ratio):
                break
                
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            
            if len(approx) == 4:
                doc_contour = c
                corners = approx.reshape(4, 2)
                break
        
        debug_img = image.copy()
        is_detected = corners is not None
        
        if is_detected:
            cv2.drawContours(debug_img, [doc_contour], -1, (0, 255, 0), 3)
            for pt in corners:
                cv2.circle(debug_img, tuple(pt), 10, (0, 0, 255), -1)
        else:
            cv2.putText(debug_img, "No Document Detected", (50, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            
        return is_detected, corners, debug_img