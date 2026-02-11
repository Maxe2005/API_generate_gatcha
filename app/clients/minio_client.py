from minio import Minio
from app.core.config import get_settings
from app.utils.image_utils import optimize_for_web
from pathlib import Path
import io


class MinioClientWrapper:
    def __init__(self):
        self.settings = get_settings()
        self.client = Minio(
            self.settings.MINIO_ENDPOINT,
            access_key=self.settings.MINIO_ACCESS_KEY,
            secret_key=self.settings.MINIO_SECRET_KEY,
            secure=False,  # Adjust if using HTTPS
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
            policy = f"""{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Effect": "Allow",
                        "Principal": {{ "AWS": ["*"] }},
                        "Action": ["s3:GetObject"],
                        "Resource": ["arn:aws:s3:::{self.settings.MINIO_BUCKET_ASSETS}/*"]
                    }}
                ]
            }}"""
            self.client.set_bucket_policy(self.settings.MINIO_BUCKET_ASSETS, policy)

    def upload_image(
        self, bucket_name: str, filename: str, image_data: bytes, content_type: str
    ) -> str:
        """
        Uploads image bytes to MinIO and returns the public URL.
        """
        self.client.put_object(
            bucket_name,
            filename,
            io.BytesIO(image_data),
            len(image_data),
            content_type=content_type,
        )
        return f"{self.settings.MINIO_PUBLIC_URL}/{bucket_name}/{filename}"

    def ensure_default_images(
        self, init_dir: str = "init_minio", raw_prefix: str = "monsters"
    ) -> int:
        if self._bucket_has_objects(self.settings.MINIO_BUCKET_RAW):
            return 0

        init_path = Path(init_dir)
        if not init_path.exists():
            return 0

        uploaded = 0
        for file_path in init_path.iterdir():
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg"}:
                continue

            raw_bytes = file_path.read_bytes()
            raw_filename = f"{raw_prefix}/{file_path.name}"
            content_type = "image/png" if suffix == ".png" else "image/jpeg"

            self.upload_image(
                bucket_name=self.settings.MINIO_BUCKET_RAW,
                filename=raw_filename,
                image_data=raw_bytes,
                content_type=content_type,
            )

            webp_io = optimize_for_web(raw_bytes)
            webp_filename = f"{raw_prefix}/{file_path.stem}.webp"
            self.upload_image(
                bucket_name=self.settings.MINIO_BUCKET_ASSETS,
                filename=webp_filename,
                image_data=webp_io.getvalue(),
                content_type="image/webp",
            )

            uploaded += 1

        return uploaded

    def _bucket_has_objects(self, bucket_name: str) -> bool:
        try:
            for _ in self.client.list_objects(bucket_name, recursive=True):
                return True
        except Exception:
            return False
        return False
