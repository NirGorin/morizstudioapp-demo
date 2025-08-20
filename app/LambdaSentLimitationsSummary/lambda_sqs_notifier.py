# import boto3

# sns= boto3.client('sns')# lambda_sqs_notifier.py
import os, json, boto3
from botocore.exceptions import ClientError

AWS_REGION_MESSAGING = os.getenv("AWS_REGION_MESSAGING", "il-central-1")
AWS_REGION_STORAGE   = os.getenv("AWS_REGION_STORAGE", "il-central-1")
S3_BUCKET  = os.environ["S3_BUCKET_SUMMARIES"]
SES_FROM   = os.environ["SES_FROM_EMAIL"]
TEAM_EMAILS = [e.strip() for e in os.getenv("STUDIO_TEAM_EMAILS", "").split(",") if e.strip()]

s3  = boto3.client("s3",  region_name=AWS_REGION_STORAGE)
ses = boto3.client("ses", region_name=AWS_REGION_MESSAGING)

def _s3_exists(key: str) -> bool:
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NotFound", "NoSuchKey"):
            return False
        raise

def _s3_put_json(key: str, data: dict):
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(data).encode("utf-8"),
        ContentType="application/json",
        CacheControl="no-store",
    )

def _send_email(subject: str, html_body: str):
    if not TEAM_EMAILS:
        return
    ses.send_email(
        Source=SES_FROM,
        Destination={"ToAddresses": TEAM_EMAILS},
        Message={"Subject": {"Data": subject, "Charset": "UTF-8"},
                 "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}}},
    )

def lambda_handler(event, context):
    for rec in event.get("Records", []):
        body = rec.get("body")
        if not body:
            continue
        try:
            msg = json.loads(body)
            if "Message" in msg and isinstance(msg["Message"], str):
                msg = json.loads(msg["Message"])  # SNS→SQS עטיפה
        except Exception:
            continue

        if msg.get("event") != "AI_SUMMARY_CREATED":
            continue

        user_id     = msg.get("user_id")
        studio_slug = msg.get("studio_slug")
        s3_key      = msg.get("s3_key")
        inline      = msg.get("summary_json")

        if not _s3_exists(s3_key):
            if inline:
                _s3_put_json(s3_key, inline)
            else:
                _send_email(
                    subject=f"[Moriz] Missing S3 object for user {user_id}",
                    html_body=f"<p>Missing S3 object: <b>{s3_key}</b> (studio {studio_slug}).</p>",
                )
                continue

        _send_email(
            subject=f"[Moriz] AI summary ready for user {user_id}",
            html_body=f"<h3>AI Summary Created</h3>"
                      f"<ul><li>Studio: <b>{studio_slug}</b></li>"
                      f"<li>User ID: <b>{user_id}</b></li>"
                      f"<li>S3 Key: <code>{s3_key}</code></li></ul>",
        )

    return {"ok": True}
