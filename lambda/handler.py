import json
import os
from datetime import datetime, timezone

import boto3

import compose
import drift
import feed
import weather

TABLE_NAME = os.environ.get("TABLE", "driftwatch-entries")
BUCKET_NAME = os.environ.get("BUCKET", "driftwatch-web-232351199908")

ddb = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)
s3 = boto3.client("s3")


def handler(event, context):
    # weather.fetch() never raises — it degrades to unobserved internally.
    current_weather = weather.fetch()

    new_style, drift_value, seq = drift.compute_next_style(table)
    title, body = compose.compose(seq, new_style, current_weather)

    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "pk": "ENTRY",
        "sk": now,
        "seq": seq,
        "title": title,
        "body": body,
        "weather": current_weather,
        "style": new_style,
        "drift": drift_value,
        "engine": "deterministic",
    }
    table.put_item(Item=drift.to_decimal(entry))

    try:
        feed.write_feed(s3, BUCKET_NAME, table)
    except Exception as exc:
        # A dispatch is already written to DynamoDB; the feed can catch up
        # next run. Never let an S3 failure look like a missed dispatch.
        print(json.dumps({"feed_write_failed": str(exc)}))

    print(json.dumps({"wrote": now, "seq": seq, "lexicon": new_style["lexicon"], "drift": drift_value}))
    return {"ok": True, "sk": now, "seq": seq}
