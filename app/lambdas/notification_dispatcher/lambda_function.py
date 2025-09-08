import os, json, boto3

AWS_REGION = os.getenv("AWS_REGION", "il-central-1")
TOPIC_STUDIO_EMAILS_ARN = os.getenv("SNS_TOPIC_STUDIO_EMAILS_ARN")

sns = boto3.client("sns", region_name=AWS_REGION)

def _extract_sns_envelope(sqs_record_body: str) -> dict:
    """
    הודעת SNS עטופה בגוף SQS. מחזירה dict עם event_type, payload.
    """
    outer = json.loads(sqs_record_body)
    inner_msg = json.loads(outer["Message"]) if isinstance(outer.get("Message"), str) else outer["Message"]
    return inner_msg  # {"event_type": "...", "payload": {...}, "ts": ...}

def lambda_handler(event, context):
    for record in event.get("Records", []):
        env = _extract_sns_envelope(record["body"])
        if env.get("event_type") != "trainee.registered":
            continue

        p = env["payload"]
        studio_id   = p["studio_id"]
        studio_name = p["studio_name"]
        trainee_id  = p["trainee_user_id"]
        trainee_em  = p.get("trainee_email")

        subject = f"New trainee registered to {studio_name}"
        body = (
            f"A new trainee has registered to your studio.\n\n"
            f"Studio: {studio_name} (ID: {studio_id})\n"
            f"Trainee ID: {trainee_id}\n"
            f"Trainee email: {trainee_em or 'N/A'}\n"
        )

        sns.publish(
            TopicArn=TOPIC_STUDIO_EMAILS_ARN,
            Subject=subject,
            Message=body,
            MessageAttributes={
                "studio_id": {"DataType": "String", "StringValue": str(studio_id)}
            },
        )

    return {"status": "ok"}
