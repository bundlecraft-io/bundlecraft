# Cloud Fetcher Test Configuration

This document describes how to configure and run the BundleCraft cloud fetcher integration tests for AWS S3, Google Cloud Storage (GCS), and Azure Blob Storage.

## Overview

The BundleCraft Fetch Test Suite includes integration tests for cloud storage fetchers. Unlike the self-contained tests for Vault, HTTP, and API fetchers, cloud fetcher tests require pre-configured cloud storage resources and credentials.

These tests are invoked:
- Manually via the `test-bundlecraft-fetch.yaml` workflow (workflow_dispatch)
- Automatically during releases (as warnings, not blocking)

## Prerequisites

Before running cloud fetcher tests, you need to:

1. Set up cloud storage accounts and containers/buckets
2. Upload test certificate files to these storage locations
3. Configure GitHub secrets with connection details and credentials

## Test Configuration by Provider

### AWS S3 Fetcher

**Required GitHub Secrets:**

- `S3_TEST_BUCKET`: Name of the S3 bucket containing test certificates
- `S3_TEST_OBJECT_KEY`: Path/key to the certificate file in the bucket (e.g., `certs/test-ca.pem`)
- `S3_TEST_REGION`: (Optional) AWS region for the bucket (e.g., `us-east-1`)
- `AWS_ACCESS_KEY_ID`: AWS access key ID with read permissions to the bucket
- `AWS_SECRET_ACCESS_KEY`: AWS secret access key

**Required Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-test-bucket",
        "arn:aws:s3:::your-test-bucket/*"
      ]
    }
  ]
}
```

**Setup Steps:**
```bash
# 1. Create S3 bucket (if not exists)
# Note: S3 bucket names must be globally unique. Use your-org-bundlecraft-test-certs or similar
aws s3 mb s3://your-org-bundlecraft-test-certs --region us-east-1

# 2. Upload test certificate
aws s3 cp test-ca.pem s3://your-org-bundlecraft-test-certs/certs/test-ca.pem

# 3. Create IAM user with read-only access (or use existing credentials)
# 4. Add secrets to GitHub repository settings
```

### Google Cloud Storage (GCS) Fetcher

**Required GitHub Secrets:**

- `GCS_TEST_BUCKET`: Name of the GCS bucket containing test certificates
- `GCS_TEST_OBJECT_PATH`: Path to the certificate file in the bucket (e.g., `certs/test-ca.pem`)
- `GCS_TEST_PROJECT`: (Optional) GCP project ID
- `GCS_CREDENTIALS_JSON`: Service account JSON key file contents

**Required Permissions:**

The service account needs the following IAM roles:
- `roles/storage.objectViewer` (read objects from bucket)

**Setup Steps:**
```bash
# 1. Create GCS bucket (if not exists)
# Note: GCS bucket names must be globally unique within Google Cloud
gcloud storage buckets create gs://your-org-bundlecraft-test-certs --location=US

# 2. Upload test certificate
gcloud storage cp test-ca.pem gs://your-org-bundlecraft-test-certs/certs/test-ca.pem

# 3. Create service account
gcloud iam service-accounts create bundlecraft-ci-test \
  --display-name="BundleCraft CI Test"

# 4. Grant read permissions to the bucket
gcloud storage buckets add-iam-policy-binding gs://your-org-bundlecraft-test-certs \
  --member="serviceAccount:bundlecraft-ci-test@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# 5. Create and download JSON key
gcloud iam service-accounts keys create key.json \
  --iam-account=bundlecraft-ci-test@PROJECT_ID.iam.gserviceaccount.com

# 6. Copy the contents of key.json to GCS_CREDENTIALS_JSON secret in GitHub
```

### Azure Blob Storage Fetcher

**Required GitHub Secrets:**

- `AZURE_TEST_STORAGE_ACCOUNT`: Name of the Azure Storage account
- `AZURE_TEST_CONTAINER`: Name of the blob container
- `AZURE_TEST_BLOB_NAME`: Path/name of the certificate blob (e.g., `certs/test-ca.pem`)
- `AZURE_STORAGE_CONNECTION_STRING`: Connection string for the storage account

**Alternative Authentication (Managed Identity):**
If using managed identity instead of connection string, only configure:
- `AZURE_TEST_STORAGE_ACCOUNT`
- `AZURE_TEST_CONTAINER`
- `AZURE_TEST_BLOB_NAME`

**Setup Steps:**
```bash
# 1. Create storage account (if not exists)
# Note: Storage account names must be globally unique and 3-24 characters (lowercase letters and numbers only)
az storage account create \
  --name yourorgbundlecrafttest \
  --resource-group bundlecraft-ci \
  --location eastus \
  --sku Standard_LRS

# 2. Create container
az storage container create \
  --name test-certificates \
  --account-name yourorgbundlecrafttest

# 3. Upload test certificate
az storage blob upload \
  --account-name yourorgbundlecrafttest \
  --container-name test-certificates \
  --name certs/test-ca.pem \
  --file test-ca.pem

# 4. Get connection string
az storage account show-connection-string \
  --name yourorgbundlecrafttest \
  --resource-group bundlecraft-ci \
  --output tsv

# 5. Add the connection string to AZURE_STORAGE_CONNECTION_STRING secret in GitHub
```

## Running the Tests

### Manual Execution

1. Navigate to the Actions tab in the GitHub repository
2. Select the "🥏 BundleCraft Fetch Test Suite" workflow
3. Click "Run workflow"
4. Optionally specify test types to run (e.g., `s3,gcs,azure_blob`)
5. Click "Run workflow"

### Automatic Execution During Releases

The fetch test suite is automatically triggered during releases via the `release.yaml` workflow. Cloud fetcher tests run with `continue-on-error: true`, meaning:
- Test failures are logged as warnings
- Releases are not blocked by cloud test failures
- Results can be reviewed in the separate workflow run

## Test Behavior

- **Skipping Tests**: If required secrets are not configured, tests are automatically skipped with a warning message
- **Error Handling**: Tests validate that:
  - Certificate files are successfully downloaded
  - Provenance metadata is generated
  - Files are placed in the correct staged output directories
- **Artifacts**: Each test job uploads artifacts containing:
  - Downloaded certificate files
  - Generated configuration files
  - Provenance metadata

## Troubleshooting

### S3 Test Failures

**Error: "AWS credentials not found"**
- Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set in GitHub secrets
- Check that credentials have not expired

**Error: "S3 bucket not found"**
- Verify `S3_TEST_BUCKET` name is correct
- Ensure bucket exists in the specified region
- Check IAM permissions allow `s3:ListBucket`

### GCS Test Failures

**Error: "GCS credentials file not found"**
- Verify `GCS_CREDENTIALS_JSON` secret contains valid JSON
- Check that the service account exists and has not been deleted

**Error: "Access denied"**
- Verify service account has `roles/storage.objectViewer` role
- Check that bucket and object exist

### Azure Blob Test Failures

**Error: "Authentication failed"**
- Verify `AZURE_STORAGE_CONNECTION_STRING` is correct
- Check that storage account key has not been rotated

**Error: "Blob not found"**
- Verify `AZURE_TEST_CONTAINER` and `AZURE_TEST_BLOB_NAME` are correct
- Ensure blob exists in the container

## Best Practices

1. **Use Dedicated Test Resources**: Create separate storage accounts/buckets for CI testing to avoid impacting production data
2. **Minimal Permissions**: Grant only the minimum required permissions for reading test certificates
3. **Rotate Credentials**: Periodically rotate access keys and service account keys
4. **Test Certificate Content**: Use a simple, non-production certificate file for testing (e.g., a self-signed test CA)
5. **Cost Management**: Use the cheapest storage tiers and smallest file sizes to minimize costs

## Security Considerations

- **Never commit credentials**: All credentials must be stored as GitHub secrets
- **Read-only access**: Test credentials should only have read permissions
- **Separate from production**: Use separate accounts/projects/subscriptions for testing
- **Monitor access logs**: Regularly review access logs for unusual activity
- **Consider public buckets**: For truly public test certificates, consider making the bucket/container publicly readable to avoid managing credentials (but ensure no sensitive data is exposed)

## Example Test Certificate

For testing purposes, you can generate a simple self-signed certificate:

```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out test-ca.pem -days 3650 -nodes \
  -subj "/CN=BundleCraft Test CA/O=BundleCraft/C=US"
```

Then upload `test-ca.pem` to your cloud storage locations.
