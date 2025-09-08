import json
from datetime import datetime, timezone
from .aws_clients import sns
from ..core.settings import settings

def publish_event(event_type: str, payload: dict) -> None:
    """
    מפרסם אירוע עסקי לטופיק המרכזי (moriz-events) עם MessageAttribute: event_type.
    """
    envelope = {
        "event_type": event_type,
        "ts": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    sns().publish(
        TopicArn=settings.SNS_TOPIC_EVENTS_ARN,
        Message=json.dumps(envelope),
        MessageAttributes={
            "event_type": {"DataType": "String", "StringValue": event_type}
        },
        Subject=f"Moriz event: {event_type}",
    )
