# Driftwatch — build rules

**Read `CONTRACT.md` before doing anything.** Never modify it. If something in it
is wrong or impossible, stop and tell the human rather than inventing an
alternative.

---

## Environment — Windows 11, Git Bash (MINGW64)

Every script you write puts these at the top. Not optional.

```bash
export MSYS_NO_PATHCONV=1
export AWS_PAGER=""
export AWS_DEFAULT_REGION=us-east-1
```

`MSYS_NO_PATHCONV=1` stops Git Bash rewriting any argument beginning with `/`
into a Windows path. Without it, a log group name like `/aws/lambda/x` arrives as
`C:/Program Files/Git/aws/lambda/x` and AWS rejects it with a regex-constraint
error that looks like a validation bug. It is not.

`AWS_PAGER=""` stops the CLI opening a pager that swallows the terminal.

---

## Known account-level blocks — do not spend time on these

**Bedrock is blocked account-wide.** Confirmed 14 Aug, 20 Aug and 21 Aug 2026.

```
us.anthropic.claude-sonnet-4-6   -> ValidationException: Operation not allowed
us.anthropic.claude-haiku-4-5    -> ValidationException: Operation not allowed
us.amazon.nova-micro-v1:0        -> ValidationException: Operation not allowed
```

Two model families, admin credentials. Not IAM, not model-specific. Note that
`list-inference-profiles` returns 25 profiles — that API lists what exists in the
region, not what this account may invoke. **It is not evidence.** Do not call
Bedrock. Do not add a Bedrock code path. Generation is deterministic Python.

**Lambda Function URLs return 403 on this account** with a provably correct
resource policy. Do not create one. This build needs no public endpoint at all —
the frontend reads a static `feed.json` from S3.

---

## Windows path handling — three variants, all seen on this machine

1. **Git Bash rewrites leading slashes.** Fixed by `MSYS_NO_PATHCONV=1`.
2. **`aws.exe` cannot read POSIX paths even once (1) is fixed** — it is a native
   Windows binary. For `fileb://` and `file://` arguments use a **relative path**
   from the current directory. That sidesteps both problems at once.
3. **`cygpath -w` output gets mangled in turn**, producing `MalformedPolicy:
   first byte must be '{'` because the file was never opened. **Pass all JSON
   inline as a quoted string.** Never write a policy to a file and reference it.

Heuristic: if an AWS error suggests it received garbage where a file should be,
the file was never read. Stop editing the file — change how you pass it.

---

## Deploy script rules

- **Never `|| true`.** It has already hidden one real failure on this account for
  twenty minutes. Check for existence explicitly and echo a clear skip message.
- A check that always passes is worse than no check. If you grep command output,
  verify the grep actually matches on a real run — JSON escaping has silently
  broken this before.
- Every script echoes what it is about to do before doing it.
- Scripts must be safely re-runnable.
- Every heredoc is immediately followed by `cat` or `wc -l` so truncation is
  caught at write time, not at deploy time.

---

## Diagnosis rule — two attempts, then stop

If an AWS operation fails, before touching config: run the same operation
directly from the CLI. If it fails there too, it is not our code — it is the
account. Report it and stop.

**Two attempts on a verifiably correct config, then change approach. Never a
third.** SCPs and account activation state are invisible from inside the account
and produce errors describing the wrong problem. Read AWS errors as *something
refused this*, not as literal descriptions.

---

## Token discipline

This is a deadline build and context is a budget.

- Do not read files outside your owned directory. The interface you need is in
  `CONTRACT.md`.
- Do not re-read a file you just wrote.
- Do not print entire files back to the human. Print the specific lines that
  changed.
- Do not restate the plan before executing it. Execute, then report in three
  lines: what you did, what you verified, what is left.
- Do not write tests unless asked. Verify by running the real thing once.
- No summary paragraphs at the end of a turn.

---

## Verification honesty

When the human asks to see raw output, **write it to a file and tell them the
path.** Do not paste a summary and call it raw output. On the previous build an
agent claimed "raw output above" twice while showing only a summary, and
separately claimed two fixes were already applied when one was not.

If you did not run a command, do not describe its result. If a command failed,
say so plainly and move on — no apologising.

---

## Scope

Stay inside the directory you own, listed at the bottom of `CONTRACT.md`. Do not
run `npm install` anywhere. Do not add dependencies — the Lambda uses only the
Python standard library plus `boto3`, which is already in the runtime.

Commit after every milestone with a one-line message.
