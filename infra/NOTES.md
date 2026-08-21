# infra/NOTES.md

Log of AWS surprises encountered while running the scripts in this directory.
Newest entries at the bottom.

## 2026-08-21

- `setup-s3.sh` ran clean first try: create-bucket (no LocationConstraint,
  since region is us-east-1), public-access-block off, inline JSON bucket
  policy, website config — all succeeded, no retries needed. Re-run confirmed
  idempotent (head-bucket skip path works).
- `redeploy.sh` ran clean: zip -j, update-function-code, wait
  function-updated, invoke with --log-type Tail, base64 --decode. No `|| true`
  needed anywhere, no PathConv issues — used relative `fileb://infra/build/lambda.zip`
  as CLAUDE.md prescribes.
- Minor environmental note, not a failure: `zip` on PATH resolves to
  MiKTeX's `zip.exe`, not a dedicated Info-ZIP install. It behaves correctly
  (`unzip -l` and `unzip -p` both confirm handler.py lands at zip root,
  correct byte count), but if this repo is ever built on a machine without
  MiKTeX, `zip` may not be on PATH at all. Not fixing pre-emptively — no
  problem observed yet.
