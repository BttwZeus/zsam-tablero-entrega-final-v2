import boto3

from config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        aws_session_token=settings.aws_session_token or None,
    )


def upload_attachment(card_id: str, filename: str, content: bytes) -> str:
    key = f"cards/{card_id}/{filename}"
    client = get_s3_client()
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=content,
        ServerSideEncryption="AES256",
    )
    return key


def presigned_download_url(key: str, expires_in: int = 300) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires_in,
    )
