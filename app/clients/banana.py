from google import genai
from app.core.config import get_settings
from app.core.prompts import GatchaPrompts
from app.clients.minio_client import MinioClientWrapper
from PIL import Image
import os
import asyncio
import io
import uuid


# We keep the name BananaClient to minimize refactoring in other files,
# but internally it now uses Google's GenAI as requested.
class BananaClient:
    """
    Client for Image Generation.
    Now uses Google GenAI (Flash Image) as per updated requirements,
    replacing the original Banana.dev implementation.
    """

    def __init__(self):
        self.settings = get_settings()
        # Using Gemini API Key for this "Banana" client since we switched providers
        self.client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
        self.output_dir = "app/static/images"
        self.minio_client = MinioClientWrapper()

    @staticmethod
    def _optimize_for_web(image_bytes: bytes, max_height: int = 1080) -> io.BytesIO:
        img = Image.open(io.BytesIO(image_bytes))

        # Conserver le ratio mais limiter la hauteur
        if img.height > max_height:
            ratio = max_height / float(img.height)
            new_width = int(float(img.width) * float(ratio))
            img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)

        # Conversion en WebP avec compression (80% est le sweet spot)
        webp_io = io.BytesIO()
        img.save(webp_io, format="WebP", quality=80, lossless=False)
        webp_io.seek(0)
        return webp_io

    async def generate_pixel_art(self, prompt: str, filename_base: str) -> str:
        """
        Generates an image using Google's Gemini-2.5-flash-image model.
        Returns the MinIO URL of the generated image.
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
            if part.inline_data is not None and part.inline_data.data:
                # Get raw bytes directly
                raw_bytes = part.inline_data.data

                try:
                    # Convert/Ensure to PNG using PIL
                    image = Image.open(io.BytesIO(raw_bytes))
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format="PNG")
                    img_bytes = img_byte_arr.getvalue()

                    # Unique ID for this generation
                    unique_id = uuid.uuid4()
                    filename_raw = f"{filename_base}_{unique_id}.png"
                    filename_asset = f"{filename_base}_{unique_id}.webp"

                    # 1. Upload Master (PNG 4K) to RAW bucket
                    self.minio_client.upload_image(
                        bucket_name=self.settings.MINIO_BUCKET_RAW,
                        filename=f"monsters/{filename_raw}",  # Store in /monsters/ subfolder
                        image_data=img_bytes,
                        content_type="image/png",
                    )

                    # 2. Optimize for Web
                    webp_io = self._optimize_for_web(img_bytes)
                    webp_bytes = webp_io.getvalue()

                    # 3. Upload Asset (WebP) to ASSETS bucket
                    image_url = self.minio_client.upload_image(
                        bucket_name=self.settings.MINIO_BUCKET_ASSETS,
                        filename=filename_asset,
                        image_data=webp_bytes,
                        content_type="image/webp",
                    )
                    break
                except Exception as e:
                    print(f"Error processing image: {e}")
                    continue

        if not image_url:
            # Fallback or error if no image returned
            raise Exception(
                "No image data found in response. Ensure the model supports image generation."
            )

        return image_url
