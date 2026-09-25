import os
import ctypes
import cv2
import numpy as np

class ImageEnhancer:
    def __init__(self, lib_path="./libfast_enhance.so"):
        self.cpp_lib = None
        if os.path.exists(lib_path):
            try:
                self.cpp_lib = ctypes.CDLL(lib_path)
                self.cpp_lib.cpp_fast_contrast_threshold.argtypes = [
                    ctypes.POINTER(ctypes.c_ubyte),
                    ctypes.POINTER(ctypes.c_ubyte),
                    ctypes.c_int, ctypes.c_int,
                    ctypes.c_float, ctypes.c_int
                ]
                self.cpp_lib.cpp_fast_contrast_threshold.restype = None
            except Exception as e:
                print(f"[Warning] Gagal memuat C++ native library: {e}")

    def enhance(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        if self.cpp_lib is not None:
            h, w = gray.shape
            input_ptr = gray.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
            output_img = np.zeros((h, w), dtype=np.uint8)
            output_ptr = output_img.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
            
            self.cpp_lib.cpp_fast_contrast_threshold(input_ptr, output_ptr, w, h, 2.0, 15)
            return output_img
        
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(gray)
        denoised = cv2.fastNlMeansDenoising(contrast_enhanced, h=10)
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 15, 8
        )
        return binary