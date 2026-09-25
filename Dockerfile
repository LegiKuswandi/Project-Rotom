FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    g++ \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN cmake -B build && cmake --build build && cp build/libfast_enhance.so ./libfast_enhance.so || true

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py", "--input", "./dataset", "--output", "./outputs"]