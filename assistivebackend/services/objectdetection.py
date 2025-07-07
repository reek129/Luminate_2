import cv2
import numpy as np
import time
from pathlib import Path
from ultralytics import YOLO

# Load YOLO-World model
model = YOLO("../models/yolov8x-world.pt")
model.set_classes(["chair", "table", "door", "Trash bin", "outdoor stairs", "man", "woman", "people", "elevator", "spiral staircase", "wooden stairs", "concrete stairs", "stairway", "stairs", "staircase", "white staircase", "white stairs", "sign board", "banner"])

DETECTED_FOLDER = Path("detected")
DETECTED_FOLDER.mkdir(parents=True, exist_ok=True)

def detect_objects(image: np.ndarray):
    """
    Detects objects in a given image frame.
    
    :param image: Input image as a NumPy array.
    :return: JSON detection results and list of saved bounding box images.
    """
    try:
        if image is None or image.size == 0:
            print("Invalid image received for object detection")
            return {}, []
        
        # Convert image to RGB for YOLO inference but keep a copy in BGR for saving
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  
        
        # Run inference with lower confidence threshold
        results = model(image_rgb, iou=0.5, conf=0.15)  

        detections = {}
        bbox_image_paths = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls)
                class_name = result.names[class_id]
                conf = float(box.conf)

                if conf < 0.15:
                    continue

                detections[class_name] = detections.get(class_name, 0) + 1

                if class_name.lower() in {
                    "outdoor stairs", "spiral staircase", "wooden stairs", 
                    "concrete stairs", "stairway", "stairs", "staircase", 
                    "white staircase", "white stairs", "sign board", "banner", "chair", "man", "woman", "trash bin"
                }:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    height, width = image.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(width, x2), min(height, y2)

                    if (x2 - x1) < 5 or (y2 - y1) < 5:
                        continue

                    bbox_image = image[y1:y2, x1:x2].copy()
                    
                    # Convert bounding box image to BGR before saving
                    bbox_image = cv2.cvtColor(bbox_image, cv2.COLOR_RGB2BGR)

                    timestamp = int(time.time() * 1000)
                    bbox_filename = f"{class_name.replace(' ', '_')}_{timestamp}.jpg"
                    bbox_path = DETECTED_FOLDER / bbox_filename

                    if cv2.imwrite(str(bbox_path), bbox_image):
                        bbox_image_paths.append(str(bbox_path))
                        print(f"✅ Saved {class_name} bounding box at {bbox_path}")

        return detections, bbox_image_paths

    except Exception as e:
        print(f"Error in object detection: {str(e)}")
        return {}, []
