#!/bin/bash

OPERATION=$1
DEPLOY_BUCKET=$2
CONTENT_BUCKET=$3
PROFILE=$4

REGION=us-east-1

STACK_NAME=aws-cloudfront-auto-invalidator

if [ "${OPERATION}" == "ALL" ]; then
    echo "Packaging using SAM....."
    sam package \
        --template-file template.yaml \
        --output-template-file packaged.yaml \
        --s3-bucket ${DEPLOY_BUCKET} \
        --region ${REGION} \
        --profile ${PROFILE}

    echo "Deploying using SAM...."
    sam deploy \
    --template-file packaged.yaml \
        --stack-name ${STACK_NAME} \
        --capabilities CAPABILITY_IAM \
        --region ${REGION} \
        --profile ${PROFILE}
fi

# SAM only allows subscribing Lambdas to events for buckets created in the same template
# Existing buckets cannot be used so we do this to subscribe an existing bucket to the new
# functions.  See : https://github.com/awslabs/serverless-application-model/issues/124

AWS_ACCOUNT_ID=$(aws sts get-caller-identity \
                    --query 'Account' \
                    --output text \
                    --region ${REGION} \
                    --profile ${PROFILE}
)
echo "Our AWS account ID is ${AWS_ACCOUNT_ID}"

FUNCTION_NAME=$(aws cloudformation describe-stacks \
                --stack-name ${STACK_NAME} \
                --query 'Stacks[].Outputs[].OutputValue' \
                --output text \
                --region ${REGION} \
                --profile ${PROFILE}
)
echo "The Lambda function name is ${FUNCTION_NAME}"

FUNCTION_ARN=$(aws lambda get-function \
                --function-name ${FUNCTION_NAME} \
                --query 'Configuration.FunctionArn' \
                --output text \
                --region ${REGION} \
                --profile ${PROFILE}
)
echo "The Lambda function ARN is ${FUNCTION_ARN}"

# Allow the lambda to receive events from S3
echo "Adding Lambda invoke permissions..."

aws lambda add-permission \
    --function-name ${FUNCTION_NAME} \
    --region ${REGION} \
    --profile ${PROFILE} \
    --statement-id "s3perms-${CONTENT_BUCKET}" \
    --action "lambda:InvokeFunction" \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::${CONTENT_BUCKET} \
    --source-account ${AWS_ACCOUNT_ID} > /dev/null 2>&1

# Subscribe the lambda to S3 events for our specific bucket
S3_LAMBDA_EVENT_SUBSCRIPTION="{\"LambdaFunctionConfigurations\":[{\"LambdaFunctionArn\":\"${FUNCTION_ARN}\",\"Events\":[\"s3:ObjectCreated:*\"]}]}"

echo "Adding AWS event subscription for bucket ${CONTENT_BUCKET}"
aws s3api put-bucket-notification-configuration \
    --bucket ${CONTENT_BUCKET} \
    --notification-configuration ${S3_LAMBDA_EVENT_SUBSCRIPTION} \
    --region ${REGION} \
    --profile ${PROFILE} \