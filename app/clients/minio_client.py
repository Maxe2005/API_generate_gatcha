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
        # Ensure RAW bucket (Private)
        if not self.client.bucket_exists(self.settings.MINIO_BUCKET_RAW):
            self.client.make_bucket(self.settings.MINIO_BUCKET_RAW)
        
        # Ensure ASSETS bucket (Public)
        if not self.client.bucket_exists(self.settings.MINIO_BUCKET_ASSETS):
            self.client.make_bucket(self.settings.MINIO_BUCKET_ASSETS)
            # Set public policy
            policy = f'''{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Effect": "Allow",
                        "Principal": {{ "AWS": ["*"] }},
                        "Action": ["s3:GetObject"],
                        "Resource": ["arn:aws:s3:::{self.settings.MINIO_BUCKET_ASSETS}/*"]
                    }}
                ]
            }}'''
            self.client.set_bucket_policy(self.settings.MINIO_BUCKET_ASSETS, policy)

    def upload_image(self, bucket_name: str, filename: str, image_data: bytes, content_type: str) -> str:
        """
        Uploads image bytes to MinIO and returns the public URL.
        """
        self.client.put_object(
            bucket_name,
            filename,
            io.BytesIO(image_data),
            len(image_data),
            content_type=content_type
        )
        return f"{self.settings.MINIO_PUBLIC_URL}/{bucket_name}/{filename}"
