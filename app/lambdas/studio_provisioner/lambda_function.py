import os, json, boto3, logging
from datetime import datetime, timezone

AWS_REGION = os.getenv("AWS_REGION", "il-central-1")
S3_BUCKET  = os.getenv("S3_BUCKET")  # moriz-*-core
TOPIC_EVENTS_ARN = os.getenv("SNS_TOPIC_EVENTS_ARN")            # moriz-events
TOPIC_STUDIO_EMAILS_ARN = os.getenv("SNS_TOPIC_STUDIO_EMAILS_ARN")  # studio-emails

sns = boto3.client("sns", region_name=AWS_REGION)
s3  = boto3.client("s3",  region_name=AWS_REGION)

def _publish(event_type: str, payload: dict):
    sns.publish(
        TopicArn=TOPIC_EVENTS_ARN,
        Message=json.dumps({"event_type": event_type, "ts": datetime.now(timezone.utc).isoformat(), "payload": payload}),
        MessageAttributes={"event_type": {"DataType":"String","StringValue": event_type}},
        Subject=f"Moriz event: {event_type}",
    )

def _ensure_prefix(bucket: str, key: str):
    s3.put_object(Bucket=bucket, Key=key)  # "תיקייה" ריקה

def _put_json(bucket: str, key: str, data: dict):
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(data).encode("utf-8"), ContentType="application/json")

def lambda_handler(event, context):
    # קולט אירוע SNS עטוף ב-SQS: event["Records"][...]["body"] -> JSON של SNS
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        msg  = json.loads(body["Message"]) if isinstance(body.get("Message"), str) else body["Message"]

        if msg.get("event_type") != "studio.created":
            logging.info("Skipping non studio.created event")
            continue

        payload = msg["payload"]
        studio_id    = payload["studio_id"]
        studio_name  = payload["studio_name"]
        studio_email = payload["studio_email"]
        studio_slug  = payload.get("studio_slug","studio")

        base_prefix = f"studios/{studio_id}/"
        config_key  = f"{base_prefix}config/studio.json"

        # אידמפוטנטיות: אם קיים config, נניח שכבר בוצע provisioning
        try:
            s3.head_object(Bucket=S3_BUCKET, Key=config_key)
            already = True
        except s3.exceptions.ClientError:
            already = False

        if not already:
            _ensure_prefix(S3_BUCKET, base_prefix)
            _ensure_prefix(S3_BUCKET, f"{base_prefix}uploads/")
            _ensure_prefix(S3_BUCKET, f"{base_prefix}processed/")
            _ensure_prefix(S3_BUCKET, f"{base_prefix}ai/results/")
            _ensure_prefix(S3_BUCKET, f"{base_prefix}logs/audit/")

            config_doc = {
                "studio_id": studio_id,
                "studio_name": studio_name,
                "studio_slug": studio_slug,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "notifications": {"email": studio_email, "mechanism": "sns-email"},
                "features": {"ai": True, "emails_via_sns": True, "ses_enabled": False},
                "config_version": 1,
            }
            _put_json(S3_BUCKET, config_key, config_doc)

            # יוצר Subscription לאימייל של הסטודיו בטופיק studio-emails
            # שים לב: ל-protocol=email נקבל "pending confirmation" עד לאישור
            sub = sns.subscribe(
                TopicArn=TOPIC_STUDIO_EMAILS_ARN,
                Protocol="email",
                Endpoint=studio_email,
                ReturnSubscriptionArn=True,
            )
            logging.info(f"SNS email subscription created: {sub.get('SubscriptionArn')} (will be 'pending confirmation')")

        # הודעת הצלחה
        _publish("studio.provisioned", {
            "studio_id": studio_id,
            "s3_prefix": base_prefix,
            "config_key": config_key,
        })

    return {"status": "ok"}
