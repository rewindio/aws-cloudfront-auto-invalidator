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
