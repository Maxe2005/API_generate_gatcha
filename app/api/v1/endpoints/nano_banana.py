from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from app.clients.banana import BananaClient
import os
import io
from PIL import Image

router = APIRouter()


@router.post("/generate-simple")
async def generate_simple_image(
    aspect_ratio: str = Form(
        ..., description="Dimension ratio of the image, e.g., '1:1', '3:4', '16:9'"
    ),
    image_size: str = Form(
        ..., description="Size of the image, e.g., '1024x1024', '4K'"
    ),
    output_image_name: str = Form(
        ..., description="Name of the file to save (without extension or with .png)"
    ),
    prompt: str = Form(..., description="Description of image"),
    image: Optional[UploadFile] = File(
        None, description="Optional input image for generation"
    ),
):
    """
    Generate an image directly using Nano Banana (Gemini) and save it locally.
    Arguments:
    - aspect_ratio: e.g. "1:1", "3:4", "16:9"
    - image_size: e.g. "1024x1024" or logic supported by client (client uses "4K" but let's pass what user sends and let client/gemini validation handle it, though client expects logic)
    - output_image_name: Name of the file to save (without extension or with .png)
    - prompt: Description of image
    - image: Optional input image file
    """
    client = BananaClient()
    try:
        # Process input image if provided
        pil_image = None
        if image:
            contents = await image.read()
            pil_image = Image.open(io.BytesIO(contents))

        # Generate image
        image_bytes = await client.generate_custom_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            image_input=pil_image,
        )

        # Ensure directory exists
        output_dir = "classic_images_generated"
        os.makedirs(output_dir, exist_ok=True)

        # Format filename and secure it
        filename = os.path.basename(output_image_name)
        if not filename.lower().endswith(".png"):
            filename += ".png"

        file_path = os.path.join(output_dir, filename)

        # Handle duplicates: base.png -> base_1.png -> base_2.png
        if os.path.exists(file_path):
            base_name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(file_path):
                file_path = os.path.join(output_dir, f"{base_name}_{counter}{ext}")
                counter += 1

        # Save image (synchronous write is okay for small files in this context, or could be wrapped)
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        return {
            "status": "success",
            "message": "Image generated and saved successfully",
            "file_path": file_path,
            "params": {
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "prompt": prompt,
                "image_provided": bool(image),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
