import os, json, boto3
from datetime import datetime, timezone

ddb = boto3.resource("dynamodb")
table = ddb.Table(os.environ.get("TABLE", "driftwatch-entries"))

def handler(event, context):
    now = datetime.now(timezone.utc).isoformat()
    table.put_item(Item={
        "pk": "ENTRY",
        "sk": now,
        "stub": True,
        "body": "Station online. Awaiting instrumentation.",
    })
    print(json.dumps({"wrote": now}))
    return {"ok": True, "sk": now}
