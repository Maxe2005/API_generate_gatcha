import io
from PIL import Image


def optimize_for_web(image_bytes: bytes, max_height: int = 1080) -> io.BytesIO:
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
