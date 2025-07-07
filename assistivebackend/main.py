from fastapi import FastAPI, File, UploadFile, HTTPException
import numpy as np
import cv2
import time
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from collections import Counter

from services.objectdetection import detect_objects
from services.ocr import process_signboard_ocr
from services.stepcount import process_step_count
from services.tts import generate_tts_audio

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Ensure static directory exists
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
audio_dir = static_dir / "audio"
audio_dir.mkdir(exist_ok=True)

# Mount static files for audio access
app.mount("/static", StaticFiles(directory="static"), name="static")

# Define class sets
STAIR_CLASSES = {"outdoor stairs", "spiral staircase", "wooden stairs", 
                 "concrete stairs", "stairway", "stairs", "staircase", 
                 "white staircase", "white stairs"}

SIGN_CLASSES = {"sign board", "banner"}
OBJECT_CLASSES = {"cell phone", "chair", "table", "door", "trash bin"}

@app.post("/upload-frame")
async def upload_frame(file: UploadFile = File(...)):
    try:
        print(f"Received file: {file.filename}")
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image format")
        print(f"Frame received: {image.shape}")

        # Perform object detection
        detection_results, bbox_paths = detect_objects(image)
        print(f"Raw detection results: {detection_results}")

        # Count objects from detection results directly
        object_counts = {}
        
        # Process according to the type of detection_results
        if isinstance(detection_results, dict):
            # If it's already a dictionary of counts, use it directly
            for class_name, count in detection_results.items():
                object_counts[class_name.lower()] = count
                
            # Convert to list format for API response consistency
            detection_list = []
            for class_name, count in detection_results.items():
                detection_list.append({"class": class_name, "count": count})
            detection_results = detection_list
        else:
            # If it's a list of detections, count them manually
            for detection in detection_results:
                if "class" in detection:
                    obj_class = detection["class"].lower()
                    if obj_class not in object_counts:
                        object_counts[obj_class] = 0
                    object_counts[obj_class] += 1
        
        # Print the counted objects for debugging
        print(f"Counted objects: {object_counts}")

        # OCR on signboards
        ocr_results = process_signboard_ocr(bbox_paths)

        # Step count detection if stairs found
        detected_class_names = set(object_counts.keys())
        stairs_detected = bool(detected_class_names & STAIR_CLASSES)
        step_count_results = None
        formatted_step_count = None

        if stairs_detected:
            print("Stairs detected, processing step count...")
            step_count_results = process_step_count(bbox_paths)

            if "error" not in step_count_results:
                formatted_step_count = {
                    "status": "success",
                    "stairs_detected": True,
                    "results": []
                }
                for img_path, result in step_count_results.items():
                    if "step_count" in result:
                        stair_type = Path(img_path).stem.split('_')[0].replace('_', ' ')
                        formatted_step_count["results"].append({
                            "stair_type": stair_type,
                            "step_count": result["step_count"],
                            "confidence": result.get("confidence", 0),
                            "annotated_image": f"/output_frames/{Path(result['annotated_image']).name}" if "annotated_image" in result else None
                        })

        # Build scene description
        description_parts = []

        # Step info
        if formatted_step_count and formatted_step_count["status"] == "success":
            for stair_info in formatted_step_count["results"]:
                description_parts.append(
                    f"{stair_info['stair_type'].capitalize()} with {stair_info['step_count']} steps ahead."
                )

        # Function to handle pluralization properly
        def pluralize(word, count):
            # Fix "man" -> "men"
            if word.lower() == "man" and count > 1:
                return "men"
            # Handle common irregular plurals
            elif word.lower() == "person" and count > 1:
                return "people"
            # Standard pluralization
            elif count > 1:
                if word.endswith('s') or word.endswith('ch') or word.endswith('sh') or word.endswith('x'):
                    return f"{word}es"
                else:
                    return f"{word}s"
            else:
                return word

        # Function to get the correct object description
        def get_object_description(obj, count):
            if count == 1:
                article = "an" if obj[0].lower() in 'aeiou' else "a"
                return f"{article} {obj}"
            else:
                plural = pluralize(obj, count)
                return f"{count} {plural}"

        # Filter out sign classes
        filtered_counts = {obj: count for obj, count in object_counts.items() 
                          if obj not in SIGN_CLASSES}

        # Add objects with their counts
        if filtered_counts:
            object_descriptions = []
            for obj, count in filtered_counts.items():
                object_descriptions.append(get_object_description(obj, count))
            
            if len(object_descriptions) == 1:
                description_parts.append(f"{object_descriptions[0]} ahead.")
            elif len(object_descriptions) == 2:
                description_parts.append(f"{object_descriptions[0]} and {object_descriptions[1]} ahead.")
            else:
                joined_objects = ", ".join(object_descriptions[:-1]) + f", and {object_descriptions[-1]}"
                description_parts.append(f"{joined_objects} ahead.")

        # Signboard text
        for _, text in ocr_results.items():
            clean_text = text.strip()
            if clean_text:
                description_parts.append(f"Signboard reads '{clean_text}'.")

        # Combine final description
        verbal_description = " ".join(description_parts) if description_parts else "Nothing relevant ahead."
        print(f"🗣️ Scene Description: {verbal_description}")

        # Generate TTS audio
        audio_url = generate_tts_audio(verbal_description)
        print(f"Generated audio at: {audio_url}")

        # Verify the audio file exists
        full_audio_path = Path(audio_url.lstrip("/"))
        if not Path("static").joinpath(full_audio_path.relative_to("static")).exists():
            print(f"WARNING: Audio file not found at {full_audio_path}")

        response_data = {
            "message": "Frame processed successfully",
            "detections": detection_results,
            "bounding_box_images": [f"/detected/{Path(p).name}" for p in bbox_paths],
            "ocr_results": ocr_results,
            "step_count_results": formatted_step_count,
            "scene_description": verbal_description,
            "audio_path": audio_url
        }

        print(f"Sending response with audio_path: {audio_url}")
        return response_data

    except Exception as e:
        print(f"Error processing frame: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)