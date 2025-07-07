import cv2
import time
from pathlib import Path
from paddleocr import PaddleOCR

detected_folder = Path("detected")
ocr_model = PaddleOCR(lang="en", use_angle_cls=True)

def perform_ocr(image_path: str):
    """
    Perform OCR on the given image.
    :param image_path: Path to the image file.
    :return: Extracted text as a string.
    """
    try:
        start_time = time.time()
        results = ocr_model.ocr(image_path, cls=True)
        execution_time = time.time() - start_time
        
        extracted_texts = [line[1][0] for result in results for line in result if line[1][0].strip()]
        final_text = " ".join(extracted_texts)
        
        print(f"OCR Execution Time: {execution_time:.2f}s")
        print(f"Extracted Text: {final_text}")
        
        return final_text
    except Exception as e:
        print(f"Error during OCR processing: {str(e)}")
        return ""

def process_signboard_ocr(bbox_paths):
    """
    Run OCR on detected bounding box images if they are signboards or banners.
    :param bbox_paths: List of image file paths containing detected objects.
    :return: Dictionary mapping image path to extracted text.
    """
    ocr_results = {}
    for bbox_path in bbox_paths:
        image_name = Path(bbox_path).name
        if "sign_board" in image_name.lower() or "banner" in image_name.lower():
            text = perform_ocr(str(bbox_path))
            ocr_results[image_name] = text
    return ocr_results