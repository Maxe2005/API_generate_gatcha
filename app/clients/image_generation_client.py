import logging

from google import genai
from app.core.config import get_settings
from app.core.constants import GeminiModelEnum
from app.core.prompts import GatchaPrompts
from app.clients.minio_client import MinioClientWrapper
from app.clients.image_storage import store_generated_image
from PIL import Image
import asyncio
import io
from google.genai.types import ContentListUnionDict

logger = logging.getLogger(__name__)


class ImageGenerationClient:
    """
    Client for image generation via Google GenAI (Gemini image models).

    Historical note: this class used to be called `BananaClient` and target
    Banana.dev — the service was migrated to Gemini image generation, but the
    name (and the unused `BANANA_API_KEY` setting) lingered until this rename.

    Second historical note: Gemini was later replaced by fal.ai
    (`app/clients/fal_client.py`) as the *default* image provider — see
    `app/clients/image_provider_factory.py`. This client is kept as a
    supported alternative provider (selectable via `ImageProviderEnum.GEMINI`),
    not because it's still the default.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
        self.minio_client = MinioClientWrapper()

    async def generate_pixel_art(
        self,
        prompt: str,
        filename_base: str,
        model: str | None = None,
        reference_image_bytes: bytes | None = None,
    ) -> dict:
        """
        Generates an image using a Gemini image model.
        Returns a dict with the MinIO URL and the raw image key.
        args:
            prompt: Visual description
            filename_base: sanitized monster name for the file
            model: Gemini model to use for image generation (defaults to
                GeminiModelEnum.GEMINI_3_PRO_IMAGE if not provided)
            reference_image_bytes: optional reference image bytes for
                image-to-image generation (e.g. keeping a monster's visual
                identity when generating a skill-card image)
        Returns:
            dict with keys:
                - image_url: URL of the optimized WebP image
                - raw_image_key: Object key of the 4K PNG image (internal use only)
        """
        model = model or GeminiModelEnum.GEMINI_3_PRO_IMAGE.value
        full_prompt = GatchaPrompts.IMAGE_GENERATION.format(prompt=prompt)
        reference_image = (
            Image.open(io.BytesIO(reference_image_bytes)) if reference_image_bytes else None
        )

        # The SDK is synchronous, so we run it in a thread pool to avoid blocking FastAPI
        loop = asyncio.get_running_loop()

        # Wrapped function for the thread executor
        def _generate():
            contents: ContentListUnionDict = [full_prompt]
            if reference_image is not None:
                contents.append(reference_image)

            response = self.client.models.generate_content(
                model=model,
                contents=contents,
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
                    logger.warning(f"Image generation rate limit hit. Retrying in {sleep_time}s...")
                    await asyncio.sleep(sleep_time)
                    continue
                raise Exception(f"Image Generation Error: {str(e)}") from e

        if not response or not response.parts:
            raise Exception("No content parts found in response.")

        result: dict | None = None

        # The snippet provided iterates over parts. We adapt that logic.
        for part in response.parts:
            # Inline data contains the image
            if part.inline_data is not None and part.inline_data.data:
                raw_bytes = part.inline_data.data
                try:
                    result = store_generated_image(raw_bytes, filename_base, self.minio_client)
                    break
                except Exception as e:
                    logger.warning(f"Error processing image: {e}")
                    continue

        if not result:
            # Fallback or error if no image returned
            raise Exception(
                "No image data found in response. Ensure the model supports image generation."
            )

        return result

    async def generate_custom_image(
        self,
        prompt: str,
        aspect_ratio: str,
        image_size: str,
        model: str | None = None,
        image_input: Image.Image | None = None,
    ) -> bytes:
        """
        Generates an image with custom parameters using Google's GenAI.
        Returns the raw image bytes (PNG).
        """
        model = model or GeminiModelEnum.GEMINI_3_PRO_IMAGE.value
        # The SDK is synchronous, so we run it in a thread pool to avoid blocking FastAPI
        loop = asyncio.get_running_loop()

        # Wrapped function for the thread executor
        def _generate():
            contents: ContentListUnionDict = [prompt]
            if image_input:
                contents.append(image_input)

            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    image_config=genai.types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=image_size,
                    )
                ),
            )
            return response

        try:
            response = await loop.run_in_executor(None, _generate)
        except Exception as e:
            raise Exception(f"Custom Image Generation Error: {str(e)}") from e

        if not response or not response.parts:
            raise Exception("No content parts found in response.")

        for part in response.parts:
            if part.inline_data is not None and part.inline_data.data:
                raw_bytes = part.inline_data.data
                # Convert/Ensure to PNG using PIL
                image = Image.open(io.BytesIO(raw_bytes))
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format="PNG")
                return img_byte_arr.getvalue()

        raise Exception("No image data found in response.")
