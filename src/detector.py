import cv2
import numpy as np

class DocumentDetector:
    def __init__(self, min_area_ratio=0.03): # Diturunkan ke 0.03 agar kartu yang tampak kecil/vertikal tetap terdeteksi
        self.min_area_ratio = min_area_ratio

    def detect(self, image: np.ndarray):
        h, w = image.shape[:2]
        image_area = h * w
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Cek rata-rata kecerahan gambar. Jika terindikasi gelap (< 110),
        # tingkatkan kontrasnya secara otomatis menggunakan CLAHE
        if np.mean(gray) < 110:
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            gray = clahe.apply(gray)


        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # SOLUSI 1: Mengatasi Kontras Rendah
        # Gabungkan Canny (dengan ambang sensitif) dan Otsu Thresholding 
        # agar tepi kartu yang putih di atas meja terang tetap terisolasi
        canny = cv2.Canny(blurred, 30, 100)
        _, thresh_otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        combined_edges = cv2.bitwise_or(canny, thresh_otsu)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(combined_edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        doc_contour = None
        corners = None
        
        for c in contours:
            area = cv2.contourArea(c)
            if area < (image_area * self.min_area_ratio):
                break
                
            peri = cv2.arcLength(c, True)
            # Sedikit dilonggarkan ke 0.03 agar batas tepi tidak terlalu kaku
            approx = cv2.approxPolyDP(c, 0.03 * peri, True)
            
            # SOLUSI 2: Melonggarkan Aturan len(approx) == 4
            if len(approx) == 4:
                doc_contour = c
                corners = approx.reshape(4, 2)
                break
            elif 4 < len(approx) <= 10:
                # Fallback: Jika ada bayangan yang membuat sudut terbaca 5-10 titik, 
                # paksa buat kotak area terkecil (Minimum Bounding Box) dari kontur tersebut
                rect = cv2.minAreaRect(c)
                box = cv2.boxPoints(rect)
                doc_contour = c
                corners = np.int32(box)
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