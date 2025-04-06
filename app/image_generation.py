import asyncio
import os
import logging
from google import genai
from google.genai import types
import aiofiles
from decouple import config

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configure Google Generative AI
api_key = config("IMAGE_KEY", default=None)
client = genai.Client(api_key=api_key)

# Asynchronous function to generate an image
async def generate_image_async(prompt: str, file_path: str):
    try:
        if not prompt.strip():
            logging.warning("Skipping empty prompt for image generation.")
            return
        
        response = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1),
        )

        for generated_image in response.generated_images:
            image_bytes = generated_image.image.image_bytes

            # Save the image asynchronously
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(image_bytes)
            
            logging.info(f"Image saved: {file_path}")
    
    except Exception as e:
        logging.error(f"Error generating image for '{prompt}': {str(e)}")

# Main function to process multiple image prompts asynchronously
async def process_images(prompts: list):
    try:
        if not prompts:
            raise ValueError("Image prompts list cannot be empty.")

        output_directory = "output/images"
        os.makedirs(output_directory, exist_ok=True)

        tasks = []
        for i, prompt in enumerate(prompts, start=1):
            file_path = f"{output_directory}/image_{i}.png"
            tasks.append(generate_image_async(prompt, file_path))

        await asyncio.gather(*tasks)
        logging.info("All images have been generated successfully.")
    
    except Exception as e:
        logging.error(f"Failed to process images: {str(e)}")
