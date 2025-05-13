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
