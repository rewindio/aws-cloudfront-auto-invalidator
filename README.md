# aws-cloudfront-auto-invalidator
This is a small Lambda function (packaged somewhat with AWS SAM) to auto-invalidate content in Cloudfront when the underlying S3 origin content changes.

## Requirements
* AWS CLI (configured with at least one profile)
* AWS SAM CLI
* Existing S3 bucket to store SAM Lambda code
* Existing S3 bucket and Cloudfront distribution 

## Deploying
Invoke the `deploy.sh` script in the root of the project as follows:

```
deploy.sh ALL|NEW_SUB <bucket for lambda code> <origin bucket> <AWS CLI profile name>
```

If ALL is specified as the first argument, the function will be packaged, deployed and a new event subscription will be created for the specified origin bucket.  If NEW_SUB is supplied, only a new event subscription from an origin bucket will be added (ie. use this to subscribe multiple buckets to the single function)

## Deployment Notes
Ideally, all of this solution would be a small, self-contained SAM application.  But due to [this issue](https://github.com/awslabs/aws-sam-cli/issues/206), SAM cannot subscribe events to pre-existing buckets.  Therefore, the deploy script has to add the Lambda permissions and S3 event subscription after the function has been created.  This is all performed using the AWS CLI in the deploy.sh script.

Want to monitor multiple buckets?  Just run deploy.sh with a different origin bucket (parameter 2).  You'll get a different event subscription to the Lambda function.

## Running locally
The function can be executed locally using the SAM CLI and the SampleEvent.json in the project.  You will need Docker installed to enable local execution via SAM

```
sam local invoke --event SampleEvent.json
```
This will invoke your function and pass it the contents of SampleEvent.json.  You will need to modify SampleEvent.json to represent a valid S3 bucket.

