import os
import json
import argparse
import cv2
from src.pipeline import SmartScannerPipeline

def main():
    parser = argparse.ArgumentParser(description="Rotom - Smart Document Scanner CLI")
    parser.add_argument("--input", required=True, help="Path ke file gambar atau folder dataset")
    parser.add_argument("--output", default="./outputs", help="Folder direktori output")
    args = parser.parse_args()

    os.makedirs(os.path.join(args.output, "debug"), exist_ok=True)
    os.makedirs(os.path.join(args.output, "processed"), exist_ok=True)
    os.makedirs(os.path.join(args.output, "json"), exist_ok=True)

    pipeline = SmartScannerPipeline()

    if os.path.isfile(args.input):
        files = [args.input]
    elif os.path.isdir(args.input):
        files = [
            os.path.join(args.input, f) for f in os.listdir(args.input)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
    else:
        print(f"Error: Path '{args.input}' tidak ditemukan.")
        return

    print(f"Rotom Engine memulai pemrosesan {len(files)} file...\n")

    for idx, filepath in enumerate(sorted(files), start=1):
        filename = os.path.basename(filepath)
        name_no_ext = os.path.splitext(filename)[0]
        
        metadata, debug_img, corrected_img, enhanced_img = pipeline.process(filepath)
        
        if debug_img is not None:
            cv2.imwrite(os.path.join(args.output, "debug", f"{name_no_ext}_detected.jpg"), debug_img)
        if corrected_img is not None:
            cv2.imwrite(os.path.join(args.output, "processed", f"{name_no_ext}_corrected.jpg"), corrected_img)
        if enhanced_img is not None:
            cv2.imwrite(os.path.join(args.output, "processed", f"{name_no_ext}_enhanced.jpg"), enhanced_img)
            
        json_path = os.path.join(args.output, "json", f"{name_no_ext}.json")
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        status = "DETECTED" if metadata.get("document_detected") else "❌ NO DOC"
        print(f"[{idx}/{len(files)}] {filename:<25} | {status} | Time: {metadata.get('processing_time_ms', 0)}ms | Confidence: {metadata.get('ocr_confidence', 0.0)}")

    print(f"\nPemrosesan selesai. Hasil tersimpan di folder: '{args.output}'")

if __name__ == "__main__":
    main()