from __future__ import annotations

import structlog
from botocore.exceptions import ClientError

from audib.shared.config import settings

logger = structlog.get_logger()


class S3Client:
    def __init__(self) -> None:
        import boto3

        kwargs: dict[str, object] = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": settings.AWS_REGION,
        }
        if settings.S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        self._client = boto3.client("s3", **kwargs)
        self._bucket = settings.S3_BUCKET

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
            logger.info("s3.bucket_created", bucket=self._bucket)

    def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        s3_uri = f"s3://{self._bucket}/{key}"
        logger.debug("s3.uploaded", key=key, size=len(data))
        return s3_uri

    def download_bytes(self, s3_path: str) -> bytes:
        if s3_path.startswith("s3://"):
            rest = s3_path[5:]
            bucket, key = rest.split("/", 1)
        else:
            bucket, key = self._bucket, s3_path

        response = self._client.get_object(Bucket=bucket, Key=key)
        data: bytes = response["Body"].read()
        logger.debug("s3.downloaded", key=key, size=len(data))
        return data

    def generate_presigned_url(self, key: str, expiry_seconds: int = 3600) -> str:
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )
        return url