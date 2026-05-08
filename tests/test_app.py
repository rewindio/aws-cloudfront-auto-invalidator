import pytest
from moto import mock_aws
import boto3
import os
from src.app import lambda_handler
from unittest.mock import patch


@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"


@pytest.fixture
def mock_s3(aws_credentials):
    with mock_aws():
        # Mock S3
        s3 = boto3.client("s3", region_name="us-east-1")
        yield s3


@pytest.fixture
def mock_cloudfront(aws_credentials):
    with mock_aws():
        # Mock CloudFront
        cloudfront = boto3.client("cloudfront", region_name="us-east-1")
        yield cloudfront


@pytest.fixture
def s3_and_cloudfront_setup(mock_s3, mock_cloudfront):

    bucket_name = "test-bucket"
    mock_s3.create_bucket(Bucket=bucket_name)
    mock_s3.put_object(Bucket=bucket_name, Key="test-key", Body="test-content")

    # Create CloudFront distribution
    distribution_config = {
        "CallerReference": "test-distribution",
        "Comment": "Test distribution",
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "S3-test-bucket",
                    "DomainName": f"{bucket_name}.s3.amazonaws.com",
                    "OriginPath": "",
                    "CustomHeaders": {"Quantity": 0},
                    "S3OriginConfig": {"OriginAccessIdentity": ""},
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "S3-test-bucket",
            "ViewerProtocolPolicy": "allow-all",
            "TrustedSigners": {"Enabled": False, "Quantity": 0},
            "ForwardedValues": {
                "QueryString": False,
                "Cookies": {"Forward": "none"},
                "Headers": {"Quantity": 0},
                "QueryStringCacheKeys": {"Quantity": 0},
            },
            "MinTTL": 0,
        },
        "Enabled": True,
    }
    mock_cloudfront.create_distribution(DistributionConfig=distribution_config)

    yield bucket_name, "test-key"


@pytest.fixture
def s3_and_cloudfront_regional_setup(mock_s3, mock_cloudfront, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")

    bucket_name = "test-bucket-regional"
    mock_s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
    )
    mock_s3.put_object(Bucket=bucket_name, Key="test-key", Body="test-content")

    distribution_config = {
        "CallerReference": "test-distribution-regional",
        "Comment": "Test distribution regional",
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "S3-test-bucket-regional",
                    "DomainName": f"{bucket_name}.s3.eu-west-1.amazonaws.com",
                    "OriginPath": "",
                    "CustomHeaders": {"Quantity": 0},
                    "S3OriginConfig": {"OriginAccessIdentity": ""},
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "S3-test-bucket-regional",
            "ViewerProtocolPolicy": "allow-all",
            "TrustedSigners": {"Enabled": False, "Quantity": 0},
            "ForwardedValues": {
                "QueryString": False,
                "Cookies": {"Forward": "none"},
                "Headers": {"Quantity": 0},
                "QueryStringCacheKeys": {"Quantity": 0},
            },
            "MinTTL": 0,
        },
        "Enabled": True,
    }
    mock_cloudfront.create_distribution(DistributionConfig=distribution_config)

    yield bucket_name, "test-key"


def test_lambda_handler_happy_path(s3_and_cloudfront_setup, mock_cloudfront):
    bucket_name, key = s3_and_cloudfront_setup

    # Mock event
    event = {
        "Records": [{"s3": {"bucket": {"name": bucket_name}, "object": {"key": key}}}]
    }
    # Patch the global variable in lambda_handler
    with patch("src.app.cloudfront_client", mock_cloudfront):
        # Call the lambda handler
        response = lambda_handler(event, None)

    # Assertions
    assert response == "Success"


def test_lambda_handler_regional_origin(
    s3_and_cloudfront_regional_setup, mock_cloudfront
):
    bucket_name, key = s3_and_cloudfront_regional_setup

    event = {
        "Records": [{"s3": {"bucket": {"name": bucket_name}, "object": {"key": key}}}]
    }
    with patch("src.app.cloudfront_client", mock_cloudfront):
        response = lambda_handler(event, None)

    assert response == "Success"


def _make_distribution_config(bucket_name, caller_reference):
    return {
        "CallerReference": caller_reference,
        "Comment": caller_reference,
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": f"S3-{bucket_name}",
                    "DomainName": f"{bucket_name}.s3.amazonaws.com",
                    "OriginPath": "",
                    "CustomHeaders": {"Quantity": 0},
                    "S3OriginConfig": {"OriginAccessIdentity": ""},
                }
            ],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": f"S3-{bucket_name}",
            "ViewerProtocolPolicy": "allow-all",
            "TrustedSigners": {"Enabled": False, "Quantity": 0},
            "ForwardedValues": {
                "QueryString": False,
                "Cookies": {"Forward": "none"},
                "Headers": {"Quantity": 0},
                "QueryStringCacheKeys": {"Quantity": 0},
            },
            "MinTTL": 0,
        },
        "Enabled": True,
    }


def test_lambda_handler_invalidates_all_matching_distributions(
    mock_s3, mock_cloudfront
):
    bucket_name = "shared-origin-bucket"
    mock_s3.create_bucket(Bucket=bucket_name)
    mock_s3.put_object(Bucket=bucket_name, Key="test-key", Body="test-content")

    expected_distribution_ids = set()
    for caller_ref in ("dist-a", "dist-b"):
        result = mock_cloudfront.create_distribution(
            DistributionConfig=_make_distribution_config(bucket_name, caller_ref)
        )
        expected_distribution_ids.add(result["Distribution"]["Id"])

    event = {
        "Records": [
            {"s3": {"bucket": {"name": bucket_name}, "object": {"key": "test-key"}}}
        ]
    }
    with patch("src.app.cloudfront_client", mock_cloudfront):
        response = lambda_handler(event, None)

    assert response == "Success"

    invalidated_distribution_ids = set()
    for distribution_id in expected_distribution_ids:
        invalidations = mock_cloudfront.list_invalidations(
            DistributionId=distribution_id
        )["InvalidationList"].get("Items", [])
        if invalidations:
            invalidated_distribution_ids.add(distribution_id)

    assert invalidated_distribution_ids == expected_distribution_ids
