# CONTRACT.md — Driftwatch

**FROZEN. No agent may modify this file.** If something here is wrong or
impossible, STOP and tell the human. Do not invent an alternative.

---

## What Driftwatch is

An unattended observation post. Every 15 minutes, with no human involved, it
files a dispatch about a coastline that does not exist. Real Bengaluru weather
is the only outside input. Nobody operates it — you visit and read what it has
been doing.

The second mechanism is the point: **the agent's prose style drifts based on its
own accumulated output.** Each run it measures what it has recently written and
mutates its own style parameters away from what it has overused. Those parameters
persist. Over hundreds of runs the voice measurably moves, and the site charts it.

Generation is **deterministic Python**. Bedrock is blocked account-wide on this
account (confirmed three times, two model families, AdministratorAccess attached).
Do not call Bedrock. Do not debug Bedrock. Do not add a Bedrock code path.

---

## AWS resources — exact names, already created

```
Region            us-east-1
Account           232351199908
DynamoDB table    driftwatch-entries      (pk: S, sk: S)
Lambda function   driftwatch-agent        (python3.12, handler.handler)
Lambda role       driftwatch-lambda-role
Scheduler role    driftwatch-scheduler-role
Schedule          driftwatch-tick         rate(15 minutes)
S3 bucket         driftwatch-web-232351199908     (to be created by T1)
```

Do not rename. Do not create parallel resources.

---

## Data model

Single table, two item kinds distinguished by `pk`.

### Entry item — one per agent run

```json
{
  "pk": "ENTRY",
  "sk": "2026-08-21T05:21:00.123456+00:00",
  "seq": 42,
  "title": "Dispatch 42",
  "body": "Two to four sentences of prose.",
  "weather": {
    "temp_c": 24.1,
    "code": 61,
    "label": "rain",
    "wind_kph": 12.3
  },
  "style": {
    "sentence_target": 14,
    "austerity": 0.61,
    "lexicon": "tidal",
    "repetition_pressure": 0.22
  },
  "drift": 0.08,
  "engine": "deterministic"
}
```

- `sk` is an ISO-8601 UTC timestamp. It is the sort key; newest sorts last.
- `seq` is a monotonically increasing integer starting at 1.
- `drift` is the distance between this run's style vector and the previous run's,
  in [0, 1]. First entry has `drift: 0`.
- DynamoDB rejects Python floats. Store all decimals as `Decimal`, read them back
  as `float` before JSON serialisation.

### State item — exactly one, holds the agent's evolving style

```json
{
  "pk": "STATE",
  "sk": "current",
  "seq": 42,
  "style": {
    "sentence_target": 14,
    "austerity": 0.61,
    "lexicon": "tidal",
    "repetition_pressure": 0.22
  },
  "updated_at": "2026-08-21T05:21:00.123456+00:00"
}
```

If `STATE/current` is absent, seed it with:
`sentence_target: 12, austerity: 0.5, lexicon: "tidal", repetition_pressure: 0.0, seq: 0`

---

## Style parameters — the drift mechanism

Four parameters. Three numeric and chartable, one categorical.

| Parameter | Range | Effect on prose |
|---|---|---|
| `sentence_target` | int 6–24 | mean words per sentence |
| `austerity` | float 0.0–1.0 | 0 = ornate word banks, 1 = plain word banks |
| `lexicon` | one of `tidal`, `mineral`, `avian`, `mechanical`, `botanical` | which imagery bank dominates |
| `repetition_pressure` | float 0.0–1.0 | measured, not chosen — how much this run repeated the last 20 |

### The drift rule, run once per invocation, BEFORE composing

1. Load the last 20 entries (query `pk = "ENTRY"`, `ScanIndexForward=False`, limit 20).
2. Compute `repetition_pressure` = fraction of content words in those 20 bodies
   that appear more than twice.
3. If `repetition_pressure > 0.35`, the agent is stuck. Push away:
   - switch `lexicon` to the least-used of the five across those 20 entries
   - move `austerity` by ±0.15 away from its mean across those 20
   - move `sentence_target` by ±3 away from its mean across those 20
4. Otherwise drift gently: nudge each numeric parameter by a small amount seeded
   from `sha256(previous_body)`, so movement is deterministic and reproducible
   rather than random.
5. Clamp everything to range. Write the new style to `STATE/current`.
6. `drift` = normalised euclidean distance between old and new style vectors.

**Every run must produce a different style vector than the run before it.** A flat
line on the drift chart means the mechanism is broken.

---

## Weather input

Open-Meteo. No API key, no account, no auth header.

```
https://api.open-meteo.com/v1/forecast?latitude=12.97&longitude=77.59&current=temperature_2m,weather_code,wind_speed_10m
```

Use `urllib.request` from the standard library. **No `requests`** — it is not in
the Lambda Python 3.12 runtime and adding it means packaging dependencies.

Timeout 5 seconds. **If the call fails for any reason, the run must still
produce a dispatch** using `{"temp_c": null, "code": null, "label": "unobserved",
"wind_kph": null}`. A weather outage must never mean a missed dispatch — the
agent's autonomy is the entire submission.

Map `weather_code` (WMO) to a short label: `clear`, `cloud`, `fog`, `drizzle`,
`rain`, `shower`, `storm`. Unknown codes map to `unobserved`.

---

## The S3 feed — how the frontend gets data

After writing its entry, every run overwrites `s3://driftwatch-web-232351199908/feed.json`
with `ContentType: application/json` and `CacheControl: max-age=60`.

```json
{
  "generated_at": "2026-08-21T05:21:00+00:00",
  "count": 210,
  "entries": [ "<newest first, max 60 full entry objects>" ],
  "series": [
    {"seq": 1, "t": "2026-08-21T05:21:00+00:00", "sentence_target": 12,
     "austerity": 0.5, "lexicon": "tidal", "drift": 0.0}
  ]
}
```

`series` contains **every** run ever, ordered oldest first — it is what the drift
chart plots, so it must not be truncated. `entries` is capped at 60 to keep the
file small.

**The frontend reads `feed.json` and nothing else.** No API Gateway. No fetch to
any AWS API. No credentials in the browser. Same-origin request to a static file.

---

## Frontend

Single `web/index.html` — vanilla HTML, CSS and JS. No build step, no npm, no
framework, no bundler. It must open correctly by double-clicking the local file
and by being served from the S3 website endpoint.

Required:

1. **Latest dispatch**, large, at the top — title, body, timestamp, weather label.
2. **A log of previous dispatches** below it, newest first.
3. **The drift chart** — hand-drawn inline SVG plotting `series`. Two numeric
   lines (`sentence_target` normalised, `austerity`) against `seq`, with lexicon
   changes marked. This is the single most important element on the page: it is
   the evidence that the agent ran unattended and evolved.
4. **A run counter and "last ran N minutes ago"**, computed from `generated_at`.
5. **A real dark mode with a visible toggle.** Two designed themes, not one
   inverted. Persist the choice in `localStorage`.

Constraints:

- No `crypto.randomUUID` — it does not exist over plain HTTP (S3 website endpoints
  are HTTP). Any browser API gated on secure context is banned.
- No external CDN, no chart library. Draw the SVG by hand.
- If `feed.json` fails to load, show a clear message, not a blank page.

---

## Non-negotiables

- Region is `us-east-1` everywhere.
- Deterministic generation only. No Bedrock, no external model.
- The scheduled run must never hard-fail. Wrap the weather call and the S3 write
  in try/except; a dispatch must still be written to DynamoDB if either fails.
- Never `|| true` in a shell script. Check for existence explicitly and echo a
  skip message.
- Every heredoc in a script is followed by a verification command.
- Existing rows tagged `"stub": true` are from the bootstrap. Leave them; the
  frontend filters them out.

---

## Directory ownership — strict, non-overlapping

```
T1   infra/          deploy scripts, S3 bucket setup, redeploy helper, NOTES.md
T2   lambda/         handler.py, compose.py, drift.py, weather.py, feed.py
T3   web/            index.html and nothing else
```

No agent reads or edits outside its own directory. No agent runs `npm install`.
If you need something from another layer, it is specified above — use it as
written and do not go looking at the other layer's code.

The one shared boundary: T3 consumes the `feed.json` shape defined here. T2
produces it. Neither reads the other's files.
