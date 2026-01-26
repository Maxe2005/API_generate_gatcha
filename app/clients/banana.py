from google import genai
from app.core.config import get_settings
from app.core.prompts import GatchaPrompts
import os
import asyncio


# We keep the name BananaClient to minimize refactoring in other files,
# but internally it now uses Google's GenAI as requested.
class BananaClient:
    """
    Client for Image Generation.
    Now uses Google GenAI (Flash Image) as per updated requirements,
    replacing the original Banana.dev implementation.
    """

    def __init__(self):
        settings = get_settings()
        # Using Gemini API Key for this "Banana" client since we switched providers
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.output_dir = "app/static/images"

    async def generate_pixel_art(self, prompt: str, filename_base: str) -> str:
        """
        Generates an image using Google's Gemini-2.5-flash-image model.
        Returns the local URL of the generated image.
        args:
            prompt: Visual description
            filename_base: sanitized monster name for the file
        """
        full_prompt = GatchaPrompts.IMAGE_GENERATION.format(prompt=prompt)

        # The SDK is synchronous, so we run it in a thread pool to avoid blocking FastAPI
        loop = asyncio.get_running_loop()

        # Wrapped function for the thread executor
        def _generate():
            response = self.client.models.generate_content(
                model="gemini-3-pro-image-preview",  # Using 2.0-flash or 2.5 if available as per user request example implies newer models
                contents=[full_prompt],
                config=genai.types.GenerateContentConfig(
                    image_config=genai.types.ImageConfig(
                        aspect_ratio="2:3",
                        image_size="4K",
                    )
                ),
            )
            return response

        max_retries = 3
        base_delay = 2
        response = None

        for attempt in range(max_retries):
            try:
                response = await loop.run_in_executor(None, _generate)
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e)
                if (
                    "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                ) and attempt < max_retries - 1:
                    sleep_time = base_delay * (2**attempt)
                    print(
                        f"⚠️ Image Generation Rate Limit hit. Retrying in {sleep_time}s..."
                    )
                    await asyncio.sleep(sleep_time)
                    continue
                raise Exception(f"Image Generation Error: {str(e)}") from e

        image_url = ""

        if not response or not response.parts:
            raise Exception("No content parts found in response.")

        # The snippet provided iterates over parts. We adapt that logic.
        for part in response.parts:
            # Inline data contains the image
            if part.inline_data is not None:
                # Save the image
                filename = f"{filename_base}.png"
                filepath = os.path.join(self.output_dir, filename)

                # The SDK helper .as_image() returns a PIL Image
                image = part.as_image()
                if image:
                    image.save(filepath)
                    # Construct local URL
                    image_url = f"/static/images/{filename}"
                    break

        if not image_url:
            # Fallback or error if no image returned
            raise Exception(
                "No image data found in response. Ensure the model supports image generation."
            )

        return image_url
