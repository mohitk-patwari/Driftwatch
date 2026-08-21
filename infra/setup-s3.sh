#!/usr/bin/env bash
# Creates/configures driftwatch-web-232351199908 for static website hosting
# with public read access. Safe to re-run.
set -euo pipefail

export MSYS_NO_PATHCONV=1
export AWS_PAGER=""
export AWS_DEFAULT_REGION=us-east-1

BUCKET="driftwatch-web-232351199908"

echo "=== setup-s3.sh: target bucket ${BUCKET} in ${AWS_DEFAULT_REGION} ==="

echo "--- checking whether bucket exists ---"
if aws s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
  echo "bucket ${BUCKET} already exists, skipping creation"
else
  echo "creating bucket ${BUCKET}"
  # us-east-1 is the default region; passing a LocationConstraint for it
  # is rejected by the API, so create-bucket-configuration is omitted here.
  aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_DEFAULT_REGION"
fi

echo "--- disabling public access block ---"
aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false

echo "--- verifying public access block is off ---"
PAB=$(aws s3api get-public-access-block --bucket "$BUCKET" --output text)
echo "$PAB"
if echo "$PAB" | grep -qi 'True'; then
  echo "ERROR: public access block still has a True flag set, policy below would be silently ignored"
  exit 1
fi

echo "--- applying bucket policy (public GetObject) ---"
# Passed inline as a quoted string, not via a file: aws.exe on this machine
# cannot reliably read files referenced through Git Bash / cygpath paths.
POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${BUCKET}/*"
    }
  ]
}
EOF
)
echo "$POLICY"
echo "--- policy line count (truncation check) ---"
echo "$POLICY" | wc -l

aws s3api put-bucket-policy --bucket "$BUCKET" --policy "$POLICY"

echo "--- verifying bucket policy applied ---"
aws s3api get-bucket-policy --bucket "$BUCKET" --output text

echo "--- enabling static website hosting (index.html for both index and error) ---"
aws s3api put-bucket-website --bucket "$BUCKET" --website-configuration \
  '{"IndexDocument":{"Suffix":"index.html"},"ErrorDocument":{"Key":"index.html"}}'

echo "--- verifying website configuration ---"
aws s3api get-bucket-website --bucket "$BUCKET"

echo "=== setup-s3.sh: done ==="
echo "website endpoint: http://${BUCKET}.s3-website-${AWS_DEFAULT_REGION}.amazonaws.com"
