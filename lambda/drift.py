"""The drift mechanism: measures recent output, mutates style, persists STATE.

Run once per invocation, before composing. See CONTRACT.md "Style parameters".
"""
import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from statistics import mean

from boto3.dynamodb.conditions import Key

LEXICONS = ["tidal", "mineral", "avian", "mechanical", "botanical"]

SEED_STYLE = {
    "sentence_target": 12,
    "austerity": 0.5,
    "lexicon": "tidal",
    "repetition_pressure": 0.0,
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "is", "was",
    "were", "it", "its", "with", "as", "by", "that", "this", "from", "for",
    "over", "under", "into", "out", "up", "down", "be", "are", "has", "have",
    "had", "not", "no", "but", "so", "than", "then", "there", "here",
    "which", "who", "whose", "what", "when", "where", "how", "why", "off",
    "past", "still", "already", "even", "nobody", "no", "one",
}


def to_decimal(obj):
    """Recursively convert floats to Decimal for a DynamoDB item body."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_decimal(v) for v in obj]
    return obj


def _content_words(text):
    return [
        w for w in re.findall(r"[a-z']+", text.lower())
        if w not in STOPWORDS and len(w) > 2
    ]


def _repetition_pressure(bodies):
    words = []
    for body in bodies:
        words.extend(_content_words(body))
    if not words:
        return 0.0
    counts = Counter(words)
    repeated = sum(c for c in counts.values() if c > 2)
    return repeated / len(words)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _style_floats(style):
    return {
        "sentence_target": float(style["sentence_target"]),
        "austerity": float(style["austerity"]),
        "lexicon": style["lexicon"],
        "repetition_pressure": float(style["repetition_pressure"]),
    }


def _vector_distance(old, new):
    d_sent = (new["sentence_target"] - old["sentence_target"]) / 18.0
    d_aust = new["austerity"] - old["austerity"]
    d_lex = 0.0 if new["lexicon"] == old["lexicon"] else 1.0
    d_rep = new["repetition_pressure"] - old["repetition_pressure"]
    euclid = (d_sent ** 2 + d_aust ** 2 + d_lex ** 2 + d_rep ** 2) ** 0.5
    return _clamp(euclid / 2.0, 0.0, 1.0)


def _load_state(table):
    resp = table.get_item(Key={"pk": "STATE", "sk": "current"})
    item = resp.get("Item")
    if not item:
        return dict(SEED_STYLE), 0
    return _style_floats(item["style"]), int(item.get("seq", 0))


def _load_recent_entries(table, limit=20):
    resp = table.query(
        KeyConditionExpression=Key("pk").eq("ENTRY"),
        ScanIndexForward=False,
        Limit=limit,
    )
    # Bootstrap "stub" rows have no style/body worth measuring drift against.
    return [e for e in resp.get("Items", []) if not e.get("stub") and "style" in e]


def _save_state(table, style, seq):
    table.put_item(Item=to_decimal({
        "pk": "STATE",
        "sk": "current",
        "seq": seq,
        "style": style,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }))


def compute_next_style(table):
    """Returns (new_style: dict[str,float|str], drift: float, seq: int, recent_bodies: list[str]).

    recent_bodies is the last-20-entries body text, handed back so compose()
    can avoid reusing a body line that already appears in them.
    """
    old_style, old_seq = _load_state(table)
    new_seq = old_seq + 1
    entries = _load_recent_entries(table, 20)

    if not entries:
        new_style = dict(SEED_STYLE)
        _save_state(table, new_style, new_seq)
        return new_style, 0.0, new_seq, []

    bodies = [e.get("body", "") for e in entries]
    rep = _repetition_pressure(bodies)

    new_style = dict(old_style)
    new_style["repetition_pressure"] = rep

    if rep > 0.35:
        lex_counts = Counter(e["style"]["lexicon"] for e in entries)
        new_style["lexicon"] = min(LEXICONS, key=lambda l: lex_counts.get(l, 0))

        aust_mean = mean(float(e["style"]["austerity"]) for e in entries)
        sent_mean = mean(float(e["style"]["sentence_target"]) for e in entries)
        aust_dir = 1 if old_style["austerity"] <= aust_mean else -1
        sent_dir = 1 if old_style["sentence_target"] <= sent_mean else -1

        new_style["austerity"] = _clamp(old_style["austerity"] + aust_dir * 0.15, 0.0, 1.0)
        new_style["sentence_target"] = _clamp(old_style["sentence_target"] + sent_dir * 3, 6, 24)
    else:
        digest = hashlib.sha256(bodies[0].encode()).digest()
        aust_delta = ((digest[0] / 255.0) - 0.5) * 0.1   # +/- 0.05
        sent_delta = ((digest[1] / 255.0) - 0.5) * 4.0   # +/- 2
        new_style["austerity"] = _clamp(old_style["austerity"] + aust_delta, 0.0, 1.0)
        new_style["sentence_target"] = _clamp(
            round(old_style["sentence_target"] + sent_delta), 6, 24
        )
        if digest[2] % 5 == 0:
            idx = LEXICONS.index(old_style["lexicon"])
            new_style["lexicon"] = LEXICONS[(idx + 1) % len(LEXICONS)]

    if new_style == old_style:
        # Contract: every run must produce a different style vector.
        at_max = new_style["sentence_target"] >= 24
        new_style["sentence_target"] += -1 if at_max else 1

    drift = _vector_distance(old_style, new_style)
    _save_state(table, new_style, new_seq)
    return new_style, drift, new_seq, bodies


def demo():
    assert _repetition_pressure([]) == 0.0
    rep = _repetition_pressure(["the salt tide the salt tide the salt tide crossed"])
    assert 0.0 < rep <= 1.0

    # A weather sentence repeated verbatim across dispatches must register as
    # pressure too — repetition_pressure scans whole bodies, weather sentence
    # included, so a stale phrase moves the measurement same as any other text.
    stale_weather = "a fine rain pocks the flats without committing"
    fillers = ["gulls stand on the sandbar", "the jetty is still standing",
               "nothing moved on the water today", "the channel is calm this morning"]
    stale_bodies = [f"{stale_weather}, wind is barely moving at 5 kph. {f}." for f in fillers]
    assert _repetition_pressure(stale_bodies) > _repetition_pressure(fillers)

    old = {"sentence_target": 12.0, "austerity": 0.5, "lexicon": "tidal", "repetition_pressure": 0.0}
    same = dict(old)
    assert _vector_distance(old, same) == 0.0
    near_min = {"sentence_target": 6.0, "austerity": 0.0, "lexicon": "tidal", "repetition_pressure": 0.0}
    far = {"sentence_target": 24.0, "austerity": 1.0, "lexicon": "mineral", "repetition_pressure": 1.0}
    assert _vector_distance(near_min, far) == 1.0

    d = to_decimal({"a": 1.5, "b": [0.1, {"c": 2.0}]})
    assert isinstance(d["a"], Decimal) and isinstance(d["b"][1]["c"], Decimal)
    print("drift.py OK")


if __name__ == "__main__":
    demo()
