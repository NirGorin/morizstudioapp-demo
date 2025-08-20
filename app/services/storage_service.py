# app/services/storage_service.py
import os, json, time, boto3
from botocore.exceptions import ClientError

_S3 = boto3.client("s3", region_name=os.getenv("AWS_REGION_STORAGE", "il-central-1"))
_BUCKET = os.environ["S3_BUCKET_SUMMARIES"]

def build_s3_key(studio_slug: str, user_id: int) -> str:
    ts = int(time.time())
    return f"{studio_slug}/users/{user_id}/ai_summary_{ts}.json"

def put_json_to_s3(data: dict, s3_key: str) -> str:
    _S3.put_object(
        Bucket=_BUCKET,
        Key=s3_key,
        Body=json.dumps(data).encode("utf-8"),
        ContentType="application/json",
        CacheControl="no-store",
    )
    return s3_key

def get_json_from_s3(s3_key: str) -> dict | None:
    try:
        obj = _S3.get_object(Bucket=_BUCKET, Key=s3_key)
        return json.loads(obj["Body"].read())
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise
