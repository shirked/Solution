import asyncio
import os
import logging
from google.cloud import texttospeech

# Configure logging
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

# Configure logging
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

def generate_voiceover(text: str, file_path: str):
    try:
        if not text.strip():
            raise ValueError("Voiceover text cannot be empty.")

        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-IN",
            name="en-IN-Chirp3-HD-Zephyr" # Set the desired voice
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        with open(file_path, "wb") as out:
            out.write(response.audio_content)
            print(f'Audio content written to "{file_path}"')

    except ValueError as ve:
        logging.error(f"Validation Error: {ve}")
    except Exception as e:
        logging.error(f"Error generating voiceover for text '{text}': {str(e)}")

async def generate_voiceover_async(text: str, file_path: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, generate_voiceover, text, file_path)

async def process_voiceovers(voiceover_texts: list):
    try:
        if not voiceover_texts:
            raise ValueError("Voiceover texts list cannot be empty.")
        
        output_directory = "output/voiceovers"
        os.makedirs(output_directory, exist_ok=True)  # Ensure the output folder exists

        tasks = []
        for i, item in enumerate(voiceover_texts, start=1):
            text = item.get("text", "").strip()
            if not text:
                logging.warning(f"Skipping empty text for voiceover {i}.")
                continue
            
            file_path = f"{output_directory}/voiceover_{i}.mp3"
            tasks.append(generate_voiceover_async(text, file_path))

        await asyncio.gather(*tasks)  # Run all tasks concurrently
        print("All voiceovers have been generated successfully.")
    except ValueError as ve:
        logging.error(f"Validation Error: {ve}")
    except Exception as e:
        logging.error(f"Failed to process voiceovers: {str(e)}")
