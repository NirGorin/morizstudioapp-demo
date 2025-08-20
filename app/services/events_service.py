# app/services/events_service.py
import os, json, boto3

_SNS = boto3.client("sns", region_name=os.getenv("AWS_REGION_MESSAGING", "il-central-1"))
_TOPIC_ARN = os.environ["SNS_TOPIC_AI_SUMMARY_CREATED"]

def publish_ai_summary_created(user_id: int, studio_slug: str, s3_key: str, inline_json: dict | None = None):
    msg = {"event": "AI_SUMMARY_CREATED", "user_id": user_id, "studio_slug": studio_slug, "s3_key": s3_key}
    if inline_json:
        try:
            blob = json.dumps(inline_json)
            if len(blob) <= 2000:
                msg["summary_json"] = inline_json
        except Exception:
            pass
    _SNS.publish(
        TopicArn=_TOPIC_ARN,
        Message=json.dumps(msg),
        MessageAttributes={
            "event_type": {"DataType": "String", "StringValue": "AI_SUMMARY_CREATED"},
            "studio_slug": {"DataType": "String", "StringValue": studio_slug},
        },
    )
