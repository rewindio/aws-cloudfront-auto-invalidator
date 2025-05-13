#! /usr/bin/env bash

# SAM only allows subscribing Lambdas to events for buckets created in the same template
# Existing buckets cannot be used so we do this to subscribe an existing bucket to the new
# functions.  See : https://github.com/awslabs/serverless-application-model/issues/124

OPERATION=$1
DEPLOY_BUCKET=$2
CONTENT_BUCKET=$3
PROFILE=$4

REGION=us-east-1

AWS_ACCOUNT_ID=$(aws sts get-caller-identity \
                    --query 'Account' \
                    --output text \
                    --region "${REGION}"
)
echo "Our AWS account ID is ${AWS_ACCOUNT_ID}"

FUNCTION_NAME=$(aws cloudformation describe-stacks \
                --stack-name "${STACK_NAME}" \
                --query 'Stacks[].Outputs[].OutputValue' \
                --output text \
                --region "${REGION}"
)
echo "The Lambda function name is ${FUNCTION_NAME}"

FUNCTION_ARN=$(aws lambda get-function \
                --function-name "${FUNCTION_NAME}" \
                --query 'Configuration.FunctionArn' \
                --output text \
                --region "${REGION}"
)
echo "The Lambda function ARN is ${FUNCTION_ARN}"

# Allow the lambda to receive events from S3
echo "Adding Lambda invoke permissions..."

aws lambda add-permission \
    --function-name "${FUNCTION_NAME}" \
    --region "${REGION}" \
    --statement-id "s3perms-${CONTENT_BUCKET}" \
    --action "lambda:InvokeFunction" \
    --principal s3.amazonaws.com \
    --source-arn "arn:aws:s3:::${CONTENT_BUCKET}" \
    --source-account "${AWS_ACCOUNT_ID}" > /dev/null 2>&1

# Subscribe the lambda to S3 events for our specific bucket
S3_LAMBDA_EVENT_SUBSCRIPTION="{\"LambdaFunctionConfigurations\":[{\"LambdaFunctionArn\":\"${FUNCTION_ARN}\",\"Events\":[\"s3:ObjectCreated:*\"]}]}"

echo "Adding AWS event subscription for bucket ${CONTENT_BUCKET}"
aws s3api put-bucket-notification-configuration \
    --bucket "${CONTENT_BUCKET}" \
    --notification-configuration "${S3_LAMBDA_EVENT_SUBSCRIPTION}" \
    --region "${REGION}"
