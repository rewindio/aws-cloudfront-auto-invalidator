from __future__ import print_function
import boto3
import json
import urllib
import time

cloudfront_client = boto3.client('cloudfront')

def get_cloudfront_distribution_id(bucket):
    
    bucket_origin = bucket + '.s3.amazonaws.com'
    cf_distro_id = None

    # Create a reusable Paginator
    paginator = cloudfront_client.get_paginator('list_distributions')

    # Create a PageIterator from the Paginator
    page_iterator = paginator.paginate()

    for page in page_iterator:
        for distribution in page['DistributionList']['Items']:
            for cf_origin in distribution['Origins']['Items']:
                    print("Origin found {}".format(cf_origin['DomainName']))
                    if bucket_origin == cf_origin['DomainName']:
                            cf_distro_id = distribution['Id']
                            print("The CF distribution ID for {} is {}".format(bucket,cf_distro_id))

    return cf_distro_id


# --------------- Main handler ------------------
def lambda_handler(event, context):
    '''
    Creates a cloudfront invalidation for content added to an S3 bucket
    '''
    # Log the the received event locally.
    # print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event.
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    if not key.startswith('/'):
        key = '/' + key
 
    cf_distro_id = get_cloudfront_distribution_id(bucket)

    if cf_distro_id:
        print("Creating invalidation for {} on Cloudfront distribution {}".format(key,cf_distro_id))

        try:
            invalidation = cloudfront_client.create_invalidation(DistributionId=cf_distro_id,
                    InvalidationBatch={
                    'Paths': {
                            'Quantity': 1,
                            'Items': [key]
                    },
                    'CallerReference': str(time.time())
            })

            print("Submitted invalidation. ID {} Status {}".format(invalidation['Invalidation']['Id'],invalidation['Invalidation']['Status']))
        except Exception as e:
            print("Error processing object {} from bucket {}. Event {}".format(key, bucket, json.dumps(event, indent=2)))
            raise e
    else:
        print("Bucket {} does not appeaer to be an origin for a Cloudfront distribution".format(bucket))

    return 'Success'
