from minio import Minio
from app.core.config import get_settings
import io

class MinioClientWrapper:
    def __init__(self):
        self.settings = get_settings()
        self.client = Minio(
            self.settings.MINIO_ENDPOINT,
            access_key=self.settings.MINIO_ACCESS_KEY,
            secret_key=self.settings.MINIO_SECRET_KEY,
            secure=False  # Adjust if using HTTPS
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        if not self.client.bucket_exists(self.settings.MINIO_BUCKET_NAME):
            self.client.make_bucket(self.settings.MINIO_BUCKET_NAME)
            # Set public policy
            policy = f'''{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Effect": "Allow",
                        "Principal": {{ "AWS": ["*"] }},
                        "Action": ["s3:GetObject"],
                        "Resource": ["arn:aws:s3:::{self.settings.MINIO_BUCKET_NAME}/*"]
                    }}
                ]
            }}'''
            self.client.set_bucket_policy(self.settings.MINIO_BUCKET_NAME, policy)

    def upload_image(self, filename: str, image_data: bytes, content_type: str = "image/png") -> str:
        """
        Uploads image bytes to MinIO and returns the public URL.
        """
        self.client.put_object(
            self.settings.MINIO_BUCKET_NAME,
            filename,
            io.BytesIO(image_data),
            len(image_data),
            content_type=content_type
        )
        return f"{self.settings.MINIO_PUBLIC_URL}/{self.settings.MINIO_BUCKET_NAME}/{filename}"
