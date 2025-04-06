from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.script_generation import fetch_script_from_gemini
from app.voiceover_generation import process_voiceovers
from app.image_generation import process_images
from app.video_assembly import assemble_video
from google.cloud import storage
import asyncio
import json
import os
import aiofiles
import logging
from functools import lru_cache
from decouple import config
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Cache environment variables for performance
@lru_cache()
def get_google_credentials():
    return config("GOOGLE_APPLICATION_CREDENTIALS")

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config("GOOGLE_APPLICATION_CREDENTIALS")

# Load Google Cloud Storage bucket name
BUCKET_NAME = config("BUCKET")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Input validation model
class VideoRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=100)

# Function to upload video to Google Cloud Storage
def upload_to_gcs(local_file_path, bucket_name, destination_blob_name):
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_file_path)
        logger.info(f"File {local_file_path} uploaded to {destination_blob_name} in bucket {bucket_name}.")
        return f"https://storage.googleapis.com/{bucket_name}/{destination_blob_name}"
    except Exception as e:
        logger.error(f"Error uploading to Cloud Storage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

# Async function to save JSON file
async def save_json_async(filename, data):
    try:
        async with aiofiles.open(filename, "w") as file:
            await file.write(json.dumps(data, indent=4))
    except Exception as e:
        logger.error(f"Error saving JSON: {str(e)}")
        raise HTTPException(status_code=500, detail=f"JSON save error: {str(e)}")

@app.post("/create-video/")
async def video_creation(request: VideoRequest):
    try:
        topic = request.topic.strip()
        script = fetch_script_from_gemini(topic)

        if "error" in script:
            raise HTTPException(status_code=500, detail=f"Gemini API error: {script['error']}")

        title = script.get("title", "No title provided")
        introduction = script.get("introduction", {})
        print("Data type of introduction:- ", type(introduction))
        sections = script.get("sections", [])
        conclusion = script.get("conclusion", {})

        voiceover_texts = []
        if introduction.get("voiceover"):
            voiceover_texts.append({"part": "Introduction", "text": introduction["voiceover"]})
        for i, section in enumerate(sections):
            if section.get("voiceover"):
                voiceover_texts.append({"part": f"Section {i+1}", "text": section["voiceover"]})
        if conclusion.get("voiceover"):
            voiceover_texts.append({"part": "Conclusion", "text": conclusion["voiceover"]})

        assembly_data = {
            "slides": {
                "title": title,
                "introduction": dict(introduction).get("slide_points", []),
                "sections": [{"heading": dict(sec).get("heading", "No heading"), "slide_points": dict(sec).get("slide_points", [])} for sec in sections],
            },
            "conclusion": {"slide_points": dict(conclusion).get("slide_points", [])},
        }

        voiceover_task = asyncio.create_task(process_voiceovers(voiceover_texts))
        image_task = asyncio.create_task(process_images([section.get("image_placeholder") for section in [introduction] + sections + [conclusion] if section.get("image_placeholder")]))

        await asyncio.gather(voiceover_task, image_task)

        assembly_file = "assembly.json"
        await save_json_async(assembly_file, assembly_data)

        output_video_path = f"output/videos/{topic.replace(' ', '_')}_video.mp4"
        assemble_video(assembly_file=assembly_file, output_video_path=output_video_path)

        destination_blob_name = f"video/{topic.replace(' ', '_')}_video.mp4"
        video_url = upload_to_gcs(local_file_path=output_video_path, bucket_name=BUCKET_NAME, destination_blob_name=destination_blob_name)

        return {"status": "Video created and uploaded successfully", "video_url": video_url}
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process script: {str(e)}")
