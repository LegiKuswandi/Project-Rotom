# Rotom — Smart Document Scanner & OCR Service

A production-oriented image processing pipeline that detects a document/card in a photo, corrects its perspective, enhances it for readability, runs OCR, and outputs structured JSON.

Document type implemented: **Business Card** (name, company, email, phone).

---

## 1. Setup Instructions

### 1.1 Requirements
- Python 3.10+
- CMake 3.10+ and a C++17 compiler (g++)
- Tesseract OCR (with Indonesian language pack, optional)
- OpenCV, pytesseract, numpy (see `requirements.txt`)

### 1.2 Local (non-Docker) setup
```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Build the C++ native extension (fast_enhance)
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release

# 4. Copy the compiled shared library next to app.py
cp build/libfast_enhance.so ./libfast_enhance.so   # Linux/macOS
# Windows: copy build\Release\fast_enhance.dll .\fast_enhance.dll (see note in section 8)

# 5. Make sure Tesseract is installed and on PATH
#    Ubuntu/Debian: sudo apt-get install tesseract-ocr tesseract-ocr-ind
#    Windows: install from https://github.com/UB-Mannheim/tesseract/wiki
```

### 1.3 Run
```bash
python app.py --input ./dataset --output ./outputs
```
or a single file:
```bash
python app.py --input ./dataset/card_01.jpg --output ./outputs
```

If `libfast_enhance.so` is not found or fails to load, the pipeline automatically falls back to a pure OpenCV enhancement path (see section 3.3), so the app still runs without the native build.

---

## 2. Architecture Overview

```
                       ┌──────────────────────┐
   image / folder ───► │        app.py        │  (CLI entrypoint, batch loop)
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ SmartScannerPipeline  │  (src/pipeline.py — orchestrator)
                       └──────────┬───────────┘
        ┌──────────────┬─────────┼─────────────┬───────────────┐
        ▼              ▼         ▼             ▼               ▼
 DocumentDetector  Perspective  ImageEnhancer  OCREngine  BusinessCardParser
 (src/detector.py) Corrector    (src/enhance-  (src/ocr.py) (src/parser.py)
                    (src/         ment.py, calls
                    perspective.  into C++ via
                    py)           ctypes)
```

**Data flow per image**
1. `app.py` discovers input file(s) and calls `SmartScannerPipeline.process()` for each.
2. `DocumentDetector.detect()` finds the document contour/corners and produces a debug overlay image.
3. `PerspectiveCorrector.transform()` warps the detected quadrilateral into a top-down rectangle.
4. `ImageEnhancer.enhance()` produces a binarized, OCR-friendly image — using the C++ extension when available, otherwise an OpenCV fallback.
5. `OCREngine.extract_text()` runs Tesseract on the corrected grayscale image and returns raw text + a confidence score.
6. `BusinessCardParser.parse()` extracts structured fields (name, company, email, phone) from the raw text.
7. A **180°-rotation fallback** re-runs OCR if no contact fields were found, to handle upside-down cards.
8. `app.py` writes three artifacts per image plus a metadata JSON:
   - `outputs/debug/<name>_detected.jpg` — contour/corner overlay
   - `outputs/processed/<name>_corrected.jpg` — perspective-corrected image
   - `outputs/processed/<name>_enhanced.jpg` — OCR-enhanced binary image
   - `outputs/json/<name>.json` — metadata + parsed fields

### Module responsibilities
| Module | Responsibility |
|---|---|
| `src/detector.py` | Grayscale conversion, optional CLAHE brightening, Canny edge detection, morphological closing, contour filtering, 4-point/quad approximation, debug visualization |
| `src/perspective.py` | Corner ordering (TL/TR/BR/BL), homography computation, warping, auto-rotation for portrait/landscape consistency, border cropping |
| `src/enhancement.py` | Loads the native `libfast_enhance.so` via `ctypes`; falls back to CLAHE + denoising + adaptive threshold in pure OpenCV |
| `cpp/src/fast_enhance.cpp` | C++ implementation of a fast local-contrast thresholding operation, exposed through a C ABI (`extern "C"`) for `ctypes` interop |
| `src/ocr.py` | Wraps `pytesseract`, computes an average confidence score from word-level OCR data |
| `src/parser.py` | Regex-based field extraction (email, phone) and heuristic name/company detection from non-contact text lines |
| `src/pipeline.py` | Orchestrates all stages, times execution, assembles the metadata dictionary, implements the upside-down fallback |
| `app.py` | CLI argument parsing, batch/single-file dispatch, writing outputs to disk, progress logging |

---

## 3. Algorithm Explanation & Preprocessing Decisions

### 3.1 Document Detection (`src/detector.py`)
- **Low-light compensation:** if the mean grayscale intensity is below 110, CLAHE (`clipLimit=2.5`, `tileGridSize=8x8`) is applied before edge detection. This was chosen over a global histogram equalization because CLAHE avoids over-amplifying noise in already-dark regions and works well on shadowed photos.
- **Edge detection:** `GaussianBlur(5x5)` → `Canny(30, 100)` — the relatively low thresholds were chosen to keep faint edges from low-lighting or low-contrast document borders, at the cost of some extra noise, which is then cleaned up by morphology.
- **Morphological closing** (`5x5` rect kernel, 2 iterations) bridges small gaps in the Canny edges (e.g. from partial shadows or blur) so the document outline forms one continuous contour.
- **Contour filtering:**
  - Contours are sorted by area, largest first.
  - Any contour covering more than 85% of the frame is skipped (this is almost always the image border, not the document).
  - The loop stops once contours fall below 3% of the frame area (`min_area_ratio`), since smaller shapes are treated as noise, not candidate documents.
  - `approxPolyDP` (3% of perimeter) is used to simplify the contour:
    - If it reduces to **exactly 4 points**, that quad is used directly (ideal case — a clean rectangular card/document).
    - If it reduces to **5–10 points** (common for cards with rounded corners, JPEG artefacts, or partial occlusion), a `minAreaRect` bounding box is used instead as a robust fallback.
- **Multiple-object handling:** because contours are processed largest-first and filtered by area ratio, the pipeline naturally selects the most prominent card/document-shaped object in the frame rather than smaller background clutter.
- **No-document case:** if no contour satisfies the shape/area constraints, `is_detected = False` is returned with an annotated debug image ("No Document Detected"), and the pipeline degrades gracefully (see section 3.5).

### 3.2 Perspective Correction (`src/perspective.py`)
- Corners are ordered into top-left/top-right/bottom-right/bottom-left using the classic **sum/difference heuristic** (`sum` is smallest at TL, largest at BR; `diff` is smallest at TR, largest at BL).
- Output width/height are computed as the **max** of the two opposing edge lengths, which keeps the aspect ratio stable even when the input contour is slightly skewed.
- `cv2.getPerspectiveTransform` + `cv2.warpPerspective` perform the homography.
- **Auto-rotation:** if the resulting warp is much taller than wide (`height > 1.2 × width`), it is rotated 90° clockwise. This handles cases where the detected quad's point ordering yields a "sideways" business card.
- A small **2% border crop** on each side removes residual card edges/background pixels that often remain right at the boundary after warping, which otherwise hurt OCR accuracy.

### 3.3 Image Enhancement (`src/enhancement.py` + C++)
Two paths, selected automatically:
1. **C++ native path (preferred, when `libfast_enhance.so` loads successfully):**
   `cpp_fast_contrast_threshold` (see `cpp/src/fast_enhance.cpp`) performs:
   - a global min/max contrast stretch (normalizes the full intensity range to 0–255), then
   - a **sparse local-window comparison threshold**: for each pixel it samples a `block_size × block_size` neighborhood using a stride of 2 (to keep it fast), averages the sampled neighbors, and binarizes the stretch-normalized pixel against `local_average − 10`.
   - This is a lightweight, from-scratch approximation of adaptive thresholding, written in C++ and called via `ctypes` to demonstrate the required Python↔C++ integration and to show a measurable performance path for a hot loop (per-pixel neighborhood averaging) that would be slow in pure Python.
2. **OpenCV fallback path (used when the native library isn't built/available):**
   `CLAHE(clip=2.5)` → `fastNlMeansDenoising(h=10)` → `adaptiveThreshold(GAUSSIAN_C, blockSize=15, C=8)`.
   This path is slower but does not require a compiled artifact, keeping the CLI usable out-of-the-box.

Both paths converge on the same goal: a **binarized, high local-contrast image** that Tesseract can segment reliably, since OCR engines are far more sensitive to local contrast and noise than to color information.

### 3.4 OCR (`src/ocr.py`)
- `pytesseract.image_to_data` (PSM default) is used to obtain per-word confidences; `pytesseract.image_to_string(config='--psm 3')` (fully automatic page segmentation) is used for the actual text, since business cards have no single dominant text block/column.
- Average confidence is computed only over words with a valid, positive confidence value, normalized to a 0–1 float to match the required `ocr_confidence` metadata field.
- Windows convenience: if no explicit `tesseract_cmd` is given, the class probes the default Windows install path.

### 3.5 Structured Field Parsing (`src/parser.py`)
- **Email:** standard RFC-like regex match on any line.
- **Phone:** a general phone-number regex identifies candidate lines; the full line is kept (after cleanup) rather than just the regex match, since business-card phone numbers often include labels/formatting the regex doesn't fully capture.
- **Name / Company:** heuristic — after removing lines that matched email/phone patterns or contain contact keywords (`web`, `www`, `http`, `fax`, `phone`, `email`), the **first remaining line** is assumed to be the name and the **second** the company. This assumes a business card's name is printed above the company name/title, which is a common (not universal) layout.
- All fields are sanitized with type-specific regex cleanup (`clean_name`, `clean_company`, `clean_email`, `clean_phone`) and default to `"N/A"` when empty or unparseable, so the JSON schema is always complete.

### 3.6 Upside-Down Fallback (`src/pipeline.py`)
If both `email` and `phone` parse to `"N/A"` after the first OCR pass, the corrected image is rotated 180° and OCR + parsing are re-run. If contact info is found on the rotated attempt, that result (and the rotated corrected/enhanced images) replace the originals, and `rotation_angle` is reported as `180.0` in the metadata. This is a pragmatic, low-cost way to recover from a common real-world failure mode (card scanned/photographed upside-down) without needing a dedicated orientation classifier.

---

## 4. OCR Approach

- **Engine:** Tesseract OCR (via `pytesseract`), chosen for its zero-GPU-dependency footprint, mature language support (including Indonesian, via `tesseract-ocr-ind`), and simple Docker installation compared to PaddleOCR/EasyOCR.
- **Input to OCR:** the binarized/contrast-enhanced grayscale image from `ImageEnhancer`, not the raw corrected color image — Tesseract's LSTM engine performs noticeably better on high-contrast, denoised binary input than on raw photographs.
- **Segmentation mode:** `--psm 3` (fully automatic page segmentation, no OSD) is used because business cards have irregular multi-block layouts (logo, name, title, contact block) rather than a single paragraph.
- **Confidence reporting:** derived from Tesseract's own per-word confidence output rather than a custom heuristic, then averaged and scaled to `[0, 1]`.
- **Extendability:** the OCR engine is isolated behind `OCREngine`, so swapping in PaddleOCR/EasyOCR only requires changing this one class (return contract: `(raw_text: str, confidence: float)`).

---

## 5. Assumptions

- The target document type for structured extraction is a **business card**; ID card/receipt parsers are not implemented (per the assignment's "choose ONE" requirement).
- Input images contain **at most one** primary document/card of interest; the largest valid quadrilateral-like contour is assumed to be the target.
- Business cards are assumed to have a roughly **rectangular, 4-corner** shape (rounded corners are tolerated via the 5–10-point fallback, but non-rectangular/die-cut cards are not specifically handled).
- Name is assumed to appear **before** the company name in reading order on the card — a common but not universal convention.
- The runtime environment can compile C++ (build-essential/cmake) and has Tesseract installed with English (and optionally Indonesian) trained data.
- Input images are standard photographic formats (`.jpg`, `.jpeg`, `.png`).

## 6. Tradeoffs

| Decision | Benefit | Cost |
|---|---|---|
| Sparse (stride-2) neighborhood sampling in C++ threshold | Faster than a dense per-pixel adaptive threshold | Slightly coarser local contrast estimate than OpenCV's `adaptiveThreshold` |
| Heuristic name/company parsing (line order) instead of NLP/NER | Zero extra dependencies, fast, fully offline | Fails on cards with atypical layouts (e.g. company name printed first, or as a logo/image with no OCR-able text) |
| `approxPolyDP` + `minAreaRect` fallback for detection | Robust to imperfect polygon approximation (5–10 points) | `minAreaRect` can slightly clip or include background on non-axis-aligned rounded cards |
| Automatic CLAHE only below a brightness threshold | Avoids unnecessary contrast changes on already well-lit images | A fixed threshold (110) may not be optimal for every scene/sensor |
| C++ enhancement is optional (falls back to OpenCV) | CLI works even without a successful native build | Two code paths to maintain and keep behaviorally consistent |
| 180° fallback only (not 90°/270°) | Cheap, covers the most common orientation error for a handheld/flatbed scan | Cards rotated 90°/270° after correction are not auto-recovered |

## 7. Limitations

- No true rotation-angle estimation is reported in metadata for the *primary* detection pass — `rotation_angle` is only populated by the 180° OCR fallback (0.0 or 180.0), not measured from the actual contour skew.
- Field parsing is regex/heuristic based; it does not use a trained NER model, so unusual card layouts, multiple phone numbers, or company logos with no machine-readable text will degrade `name`/`company` accuracy.
- Only Tesseract is wired in; PaddleOCR/EasyOCR are mentioned as allowed alternatives in the assignment but are not implemented here.
- No REST API is provided in this submission — the CLI (`app.py --input ...`) is the implemented interface option (Option A). A FastAPI/Flask wrapper can be added around `SmartScannerPipeline.process()` with minimal changes if Option B is required.
- Detection assumes a single dominant document; overlapping or stacked documents of similar size may confuse the largest-contour selection.
- The C++ library path is currently hardcoded to a Linux shared object (`libfast_enhance.so`); Windows users need to adjust the extension/build step manually (see section 8, note).

---

## 8. Testing Instructions

### 8.1 Sample dataset
Place test images under `dataset/`. A representative test set should include:

| # | Scenario | Purpose |
|---|---|---|
| 1 | Business card, straight-on, good lighting | Baseline / happy path |
| 2 | Business card, rotated ~15–30° | Detection under rotation |
| 3 | Business card, angled perspective (not top-down) | Perspective correction |
| 4 | Business card, low-light / dim room | CLAHE + OCR robustness |
| 5 | Business card, partial shadow across the text | OCR under uneven lighting |
| 6 | Business card among clutter (pen, phone, second card) | Correct object selection |
| 7 | Business card, upside-down | 180° fallback logic |
| 8 | No document in frame (empty desk) | Graceful "no document" failure |

### 8.2 Running the tests
```bash
python app.py --input ./dataset --output ./outputs
```
Inspect:
- `outputs/debug/*_detected.jpg` — verify the green contour/red corner markers sit on the correct object for each scenario.
- `outputs/processed/*_corrected.jpg` and `*_enhanced.jpg` — verify the image is right-side-up, cropped correctly, and legible.
- `outputs/json/*.json` — verify `document_detected`, `ocr_confidence`, and `fields` are populated as expected; for the "no document" case, confirm `document_detected: false` and all `fields` are `"N/A"` rather than a crash.

### 8.3 Expected results per scenario

| Scenario | Expected Result |
|---|---|
| Rotated document | `document_detected: true`; corrected image approximately upright |
| Low-light image | CLAHE engages automatically (mean gray < 110); OCR still returns non-empty text with reasonable confidence |
| Multiple objects | The largest valid card-shaped contour is selected; debug image confirms correct object |
| No document | `document_detected: false`, no crash, `fields` all `"N/A"`, debug image shows "No Document Detected" |
| Noisy image | Morphological closing keeps contour detection stable despite background texture |
| Partial shadow | Enhancement stage (CLAHE/threshold or C++ contrast stretch) keeps text legible enough for OCR |

### 8.4 Single-image debugging
```bash
python app.py --input ./dataset/card_07_upside_down.jpg --output ./outputs
```
Check the console line for that file — it prints detection status, processing time, and OCR confidence — then inspect the three corresponding output images and JSON directly.

---

## 9. Docker Usage

### 9.1 Build
```bash
docker build -t smart-scanner .
```
The image installs `build-essential`, `cmake`, `g++`, OpenCV runtime libs (`libgl1`, `libglib2.0-0`), and Tesseract (`tesseract-ocr`, `tesseract-ocr-ind`), then compiles `cpp/src/fast_enhance.cpp` into `libfast_enhance.so` during the build (`cmake -B build ... && cmake --build build`), so the container works with the accelerated C++ path out of the box.

### 9.2 Run (batch mode over a mounted dataset)

**Linux/macOS:**
```bash
docker run --rm \
  -v $(pwd)/dataset:/app/dataset \
  -v $(pwd)/outputs:/app/outputs \
  smart-scanner
```

**Windows PowerShell:**
```powershell
docker run --rm `
  -v ${PWD}/dataset:/app/dataset `
  -v ${PWD}/outputs:/app/outputs `
  smart-scanner
```

This mounts your local `dataset/` and `outputs/` folders into the container, so results are written back to your host machine. The default `CMD` runs:
```bash
python app.py --input ./dataset --output ./outputs
```

### 9.3 Run against a single file or different args
```bash
docker run --rm \
  -v $(pwd)/dataset:/app/dataset \
  -v $(pwd)/outputs:/app/outputs \
  smart-scanner \
  python app.py --input ./dataset/card_01.jpg --output ./outputs
```

### 9.4 Notes
- `.dockerignore` excludes `venv/`, `__pycache__/`, `*.pyc`, `.git/`, `build/`, and existing `outputs/*` from the build context to keep the image small and builds fast.
- If the C++ build step fails for any reason inside Docker, the Dockerfile uses `|| true` on the library copy so the image still builds successfully and the app transparently falls back to the OpenCV enhancement path at runtime.

---

## 10. Performance Notes

- **Processing time** is measured end-to-end per image (`time.time()` from image load to metadata assembly) and reported in `processing_time_ms` in each JSON output — typical business-card-sized images process in well under half a second on a modern CPU (excluding OCR, which is usually the largest single contributor).
- **C++ enhancement vs. OpenCV fallback:** the native path uses a stride-2 sparse neighborhood sample instead of a dense adaptive threshold, trading a small amount of local-contrast precision for reduced per-pixel work — this is most noticeable on larger images.
- **Batch mode** processes files sequentially; there is no multiprocessing/threading in the current implementation, so throughput scales linearly with the number of images. For larger datasets, parallelizing `app.py`'s file loop (e.g. `multiprocessing.Pool`) would be the first optimization to add.
- **Detection cost** dominates for large input photos due to Canny + contour operations on the full-resolution grayscale image; downscaling the image before detection (and rescaling corner coordinates back up) is a straightforward future optimization not currently implemented.
- **OCR** is typically the slowest single stage since Tesseract's LSTM engine runs on CPU; this is inherent to the chosen engine and would require GPU-accelerated engines (e.g. PaddleOCR with GPU) to meaningfully improve.

---

## 11. Project Structure

```
ProjectRotom/
├── cpp/
│   ├── include/
│   │   └── fast_enhance.hpp        # C ABI declaration for the native enhancement function
│   └── src/
│       └── fast_enhance.cpp        # Contrast stretch + sparse local-threshold implementation
├── dataset/                        # Sample input images (business cards)
├── outputs/
│   ├── debug/                      # Detection overlay images
│   ├── json/                       # Per-image metadata + structured fields
│   └── processed/                  # Corrected + enhanced images
├── src/
│   ├── __init__.py
│   ├── detector.py                 # Document/contour detection
│   ├── enhancement.py              # C++/OpenCV enhancement dispatch
│   ├── ocr.py                      # Tesseract OCR wrapper
│   ├── parser.py                   # Business card field parser
│   ├── perspective.py              # Perspective correction
│   └── pipeline.py                 # Orchestration
├── app.py                          # CLI entrypoint (batch/single-file)
├── CMakeLists.txt                  # Builds libfast_enhance.so
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── README.md
```

---

## 12. Deliverables Checklist

- [x] Source code
- [x] README (this file)
- [x] Dockerfile
- [x] Test scenarios (section 8)
- [x] Sample dataset (`dataset/`, to be populated per section 8.1)
- [x] Build/run instructions (sections 1 and 9)
- [x] Architecture explanation (section 2)
- [x] Assumptions & limitations (sections 5, 7)
- [ ] Deployment URL (optional bonus — not included in this submission)
