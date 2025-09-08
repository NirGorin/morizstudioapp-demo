import boto3
from ..core.settings import settings

_session = boto3.session.Session(region_name=settings.AWS_REGION)

def sns():
    return _session.client("sns")

def s3():
    return _session.client("s3")
