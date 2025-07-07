import torch
from ultralytics import YOLO
import cv2
import os
import numpy as np
from pathlib import Path

def process_step_count(image_paths):
    """
    Process stair images to count steps and annotate them
    
    :param image_paths: List of paths to cropped stair images
    :return: Dictionary containing step count results and paths to annotated images
    """
    try:
        print("Starting step count processing...")
        
        model_path = "../models/last.pt"
        print(f"Loading step count model from: {model_path}")
        

        if not os.path.exists(model_path):
            print(f"Model file not found at: {model_path}")
            return {"error": f"Model file not found at: {model_path}", "status": "failed"}
        
        model = YOLO(model_path)
        print(f"Step count model loaded successfully")

        output_folder = "output_frames"
        os.makedirs(output_folder, exist_ok=True)

        CONFIDENCE_THRESHOLD = 0.2
        results_dict = {}

        for image_path in image_paths:
            print(f"Processing image for step count: {image_path}")
            
            # Skip non-stair images
            image_filename = Path(image_path).name.lower()
            if not any(stair_type in image_filename for stair_type in 
                      ["stair", "staircase", "stairway", "ladder"]):
                print(f"Skipping non-stair image: {image_filename}")
                continue
                
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                print(f"Failed to load image: {image_path}")
                continue
                
            # Run inference
            results = model(image, conf=CONFIDENCE_THRESHOLD)
            
            # Count steps
            step_count = 0
            annotated_image = image.copy()
            
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    if confidence >= CONFIDENCE_THRESHOLD:
                        step_count += 1
                        
                        # Draw bounding box
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = f"Step {step_count}: {confidence:.2f}"
                        cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(annotated_image, label, (x1, y1 - 10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Add overall step count to the image
            cv2.putText(annotated_image, f"Total Steps: {step_count}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            
            # Save annotated image
            output_path = os.path.join(output_folder, os.path.basename(image_path))
            cv2.imwrite(output_path, annotated_image)
            
            # Add to results dictionary with count and image path
            results_dict[image_path] = {
                "step_count": step_count,
                "annotated_image": output_path,
                "confidence": float(confidence) if step_count > 0 else 0.0
            }
            
            print(f"Detected {step_count} steps in {image_path}")

        print(f"Step count processing complete. Results: {results_dict}")
        return results_dict
        
    except Exception as e:
        print(f"Error in step count processing: {str(e)}")
        return {"error": str(e), "status": "failed"}