import google.generativeai as genai
import json
import logging
import re
from decouple import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=config("SCRIPT_KEY"))

def fetch_script_from_gemini(topic: str) -> dict:
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Original Prompt (No Modifications)
        prompt = f"""
            Create an educational script about the topic '{topic}'.
            Everything should be educational.

            The script should be structured as follows:

            1. Title: A one-line title summarizing the topic.

            2. Introduction:
                - A paragraph that introduces the topic in engaging and simple language for the voiceover.
                - Include 2-3 key points for slide content summarizing the introduction.
                - Create a placeholder for an image related to the introduction. Avoid any image that cannot pass safety filter, copyrighted images, or any other image which will return NoneType object or similar error.

            3. Sections:
                - Include at least 8 sections in total.
                - Each section should have:
                    - A clear heading.
                    - A short paragraph (2-3 sentences) for the voiceover elaborating on the heading.
                    - 2-4 concise bullet points for slide content explaining the key aspects of the section.
                    - Create a placeholder for an image related to each section heading. Avoid any image that cannot pass safety filter, copyrighted images, or any other image which will return NoneType object or similar error.
                    - Keep the points to be maximum 5 to 6 words.

            4. Conclusion:
                - A brief summary paragraph for the voiceover to wrap up the topic.
                - Include 1-2 key points for the slide summarizing the main takeaways.
                - Create a placeholder for an image related to the conclusion. Avoid any image that cannot pass safety filter, copyrighted images, or any other image which will return NoneType object or similar error.

            5. JSON Output:
                - Format the script in JSON with the following structure:
                    ```json
                    {{
                        "title": "Your Title",
                        "introduction": {{
                            "voiceover": "Your Introduction for voiceover. Long paragraph to explain each point accurately.",
                            "slide_points": ["Point 1", "Point 2"],
                            "image_placeholder": "Introduction Image"
                        }},
                        "sections": [
                            {{
                                "heading": "Section Heading 1",
                                "voiceover": "Long paragraph for the voiceover to explain each point accurately",
                                "slide_points": ["Point 1", "Point 2"],
                                "image_placeholder": "Section Image"
                            }},
                            {{
                                "heading": "Section Heading 8",
                                "voiceover": "Long paragraph for the voiceover to explain each point accurately",
                                "slide_points": ["Point 1", "Point 2"],
                                "image_placeholder": "Section Image"
                            }}
                        ],
                        "conclusion": {{
                            "voiceover": "Your Conclusion for the voiceover. Long paragraph to explain each point accurately.",
                            "slide_points": ["Point 1", "Point 2"],
                            "image_placeholder": "Conclusion Image"
                        }}
                    }}
                    ```
                Ensure the response contains only valid JSON and nothing else.
        """

        response = model.generate_content(prompt)

        script_text = response.text.strip()  # Ensure no extra whitespace
        logger.info(f"Raw response from Gemini:\n{script_text}")  # Debugging

        # Extract JSON using regex (in case Gemini adds extra text)
        match = re.search(r"```json\s*([\s\S]+?)\s*```", script_text)
        if match:
            script_text = match.group(1).strip()  # Extract JSON-only content

        # Convert JSON string to Python dictionary
        script_data = json.loads(script_text)
        return script_data

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from Gemini: {e}")
        return {"error": "Invalid JSON response from Gemini API"}

    except Exception as e:
        logger.error(f"Error fetching script from Gemini: {str(e)}")
        return {"error": str(e)}
