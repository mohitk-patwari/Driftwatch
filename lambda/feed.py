"""Writes s3://<bucket>/feed.json from the DynamoDB entries table.

See CONTRACT.md "The S3 feed". The frontend reads this file and nothing else.
"""
import json
from datetime import datetime, timezone
from decimal import Decimal

from boto3.dynamodb.conditions import Key

MAX_FULL_ENTRIES = 60


def _json_default(o):
    if isinstance(o, Decimal):
        return int(o) if o % 1 == 0 else float(o)
    raise TypeError(f"not JSON serializable: {o!r}")


def _load_all_entries(table):
    items = []
    kwargs = {"KeyConditionExpression": Key("pk").eq("ENTRY"), "ScanIndexForward": True}
    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            return items
        kwargs["ExclusiveStartKey"] = last_key


def build_feed(table):
    items = _load_all_entries(table)  # oldest first

    series = [
        {
            "seq": item["seq"],
            "t": item["sk"],
            "sentence_target": item["style"]["sentence_target"],
            "austerity": item["style"]["austerity"],
            "lexicon": item["style"]["lexicon"],
            "drift": item["drift"],
        }
        for item in items
        if "style" in item and "seq" in item
    ]

    newest_first = list(reversed(items))[:MAX_FULL_ENTRIES]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(items),
        "entries": newest_first,
        "series": series,
    }


def write_feed(s3_client, bucket, table):
    feed = build_feed(table)
    body = json.dumps(feed, default=_json_default).encode("utf-8")
    s3_client.put_object(
        Bucket=bucket,
        Key="feed.json",
        Body=body,
        ContentType="application/json",
        CacheControl="max-age=60",
    )
    return feed


def demo():
    fake_items = [
        {"pk": "ENTRY", "sk": "2026-08-21T00:00:00+00:00", "seq": 1, "drift": Decimal("0"),
         "style": {"sentence_target": 12, "austerity": Decimal("0.5"), "lexicon": "tidal",
                    "repetition_pressure": Decimal("0")}},
        {"pk": "ENTRY", "sk": "2026-08-21T00:15:00+00:00", "stub": True, "body": "stub row"},
    ]

    class FakeTable:
        def query(self, **kwargs):
            return {"Items": fake_items}

    feed = build_feed(FakeTable())
    assert feed["count"] == 2
    assert len(feed["series"]) == 1  # stub row excluded, has no style/seq
    assert feed["entries"][0]["stub"] is True  # newest first, stub passed through
    json.dumps(feed, default=_json_default)  # must not raise on Decimal
    print("feed.py OK:", feed["count"], "entries,", len(feed["series"]), "series points")


if __name__ == "__main__":
    demo()
