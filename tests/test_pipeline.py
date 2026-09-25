import os
import cv2
import numpy as np
import pytest
from src.pipeline import SmartScannerPipeline

@pytest.fixture(scope="module")
def setup_test_images(tmp_path_factory):
    img_dir = tmp_path_factory.mktemp("test_data")

    # 1. Gambar kartu valid
    card_img = np.ones((400, 700, 3), dtype=np.uint8) * 255
    cv2.putText(card_img, "JOHN DOE", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(card_img, "john@example.com", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    bg = np.ones((1080, 1920, 3), dtype=np.uint8) * 180
    bg[340:740, 610:1310] = card_img
    valid_path = str(img_dir / "valid_card.jpg")
    cv2.imwrite(valid_path, bg)

    # 2. Gambar tanpa dokumen (Failure Case)
    plain_bg = np.ones((1080, 1920, 3), dtype=np.uint8) * 180
    invalid_path = str(img_dir / "no_doc.jpg")
    cv2.imwrite(invalid_path, plain_bg)

    return valid_path, invalid_path

def test_pipeline_detection(setup_test_images):
    valid_path, _ = setup_test_images
    pipeline = SmartScannerPipeline()
    metadata, _, _, _ = pipeline.process(valid_path)
    assert metadata["document_detected"] is True

def test_pipeline_no_document_graceful_failure(setup_test_images):
    _, invalid_path = setup_test_images
    pipeline = SmartScannerPipeline()
    metadata, _, _, _ = pipeline.process(invalid_path)
    assert metadata["document_detected"] is False
    assert metadata["fields"]["name"] == "N/A"
    assert metadata["processing_time_ms"] > 0