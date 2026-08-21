#!/usr/bin/env bash
# Rezips lambda/ and pushes it to the driftwatch-agent function, then does
# one invoke and prints the tailed logs. Safe to re-run.
set -euo pipefail

export MSYS_NO_PATHCONV=1
export AWS_PAGER=""
export AWS_DEFAULT_REGION=us-east-1

FUNCTION_NAME="driftwatch-agent"
BUILD_DIR="infra/build"
ZIP_PATH="${BUILD_DIR}/lambda.zip"       # relative path — aws.exe can't read POSIX/cygpath paths
RESPONSE_PATH="${BUILD_DIR}/invoke-response.json"

echo "=== redeploy.sh: packaging lambda/ -> ${ZIP_PATH} ==="
mkdir -p "$BUILD_DIR"
rm -f "$ZIP_PATH"

# -j junks the lambda/ path prefix so handler.py etc. sit at the zip root,
# matching the configured handler "handler.handler".
zip -j "$ZIP_PATH" lambda/*.py

echo "--- zip contents (truncation check) ---"
unzip -l "$ZIP_PATH"

echo "--- updating function code ---"
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://${ZIP_PATH}" \
  --query 'LastUpdateStatus' --output text

echo "--- waiting for update to finish applying ---"
aws lambda wait function-updated --function-name "$FUNCTION_NAME"

echo "--- invoking once ---"
LOG_B64=$(aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --log-type Tail \
  --cli-read-timeout 60 \
  --query 'LogResult' --output text \
  "$RESPONSE_PATH")

echo "--- invoke response payload (${RESPONSE_PATH}) ---"
cat "$RESPONSE_PATH"
echo

echo "--- tailed logs ---"
echo "$LOG_B64" | base64 --decode

echo "=== redeploy.sh: done ==="
