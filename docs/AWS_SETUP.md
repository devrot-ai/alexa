# Live AWS verification setup (free tier, least privilege)

This makes the "implemented, not live-verified" rows in the README honest ✅.
Everything below stays within the AWS free tier; total expected cost ≈ $0.

## 1. Create a least-privilege IAM user

IAM → Users → **freshkeep-hackathon** → attach this inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "FreshKeepDynamo",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DescribeTable",
        "dynamodb:CreateTable",
        "dynamodb:DeleteTable"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/FreshKeepHousehold"
    },
    {
      "Sid": "FreshKeepBedrock",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "*"
    },
    {
      "Sid": "FreshKeepTextract",
      "Effect": "Allow",
      "Action": ["textract:DetectDocumentText"],
      "Resource": "*"
    }
  ]
}
```

Create an access key → copy the key id + secret.

## 2. Put credentials in `freshkeep/.env`

```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

FRESHKEEP_STORE=dynamodb
FRESHKEEP_DYNAMO_TABLE=FreshKeepHousehold
FRESHKEEP_BEDROCK=1
FRESHKEEP_BEDROCK_REGION=us-east-1
FRESHKEEP_TEXTRACT=1
FRESHKEEP_TEXTRACT_REGION=us-east-1
```

The `.env` loader never overrides real environment variables and `.env` is gitignored.
Bedrock note: confirm your account has model access for `amazon.nova-lite-v1:0`
(Bedrock console → Model access) or set `FRESHKEEP_BEDROCK_MODEL` to another
accessed model (e.g. `anthropic.claude-3-haiku-20240307-v1:0`).

## 3. Run the verification suite

```bash
python scripts/verify_aws.py                 # DynamoDB + Bedrock (creates the table)
python scripts/verify_aws.py --cleanup       # deletes the table afterwards
python scripts/verify_aws.py --receipt-image my_receipt.jpg   # adds Textract
```

Expected output: `PASS dynamodb-roundtrip`, `PASS bedrock-router` (or a clear
reason), `PASS textract` when an image is supplied.

## 4. Cost & cleanup

- DynamoDB on-demand table with ~3 tiny requests: $0.00.
- Bedrock: one Nova-lite call (~400 max tokens): fractions of a cent.
- Textract: one page: within free tier (1,000 pages/month, first 3 months).
- Cleanup: `python scripts/verify_aws.py --cleanup` (or delete the table + IAM user in the console).
