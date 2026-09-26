FROM python:3.10-slim

# Install dependensi sistem, compiler C++, OpenCV, dan Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    g++ \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-ind \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install library Python terlebih dahulu (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code
COPY . .

# Buat direktori default jika belum ada
RUN mkdir -p dataset outputs

# Build C++ extension dalam mode Release untuk performa tinggi
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build --config Release && \
    (cp build/libfast_enhance.so ./libfast_enhance.so || true)

# SETTING ENV PENTING:
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LD_LIBRARY_PATH=/app

CMD ["python", "app.py", "--input", "./dataset", "--output", "./outputs"]