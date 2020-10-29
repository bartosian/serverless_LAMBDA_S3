import json
import boto3
import botocore
import os
import requests

def failResponse(err):
    return {
                    "statusCode": 400,
                    "body": json.dumps(err)
           }

def downloadS3File():
    BUCKET_NAME = os.environ['BUCKET_NAME']
    KEY = os.environ['BUCKET_FOLDER_PATH']
    BUCKET_FILE_NAME = os.environ['BUCKET_FILE_NAME']
    LOCAL_FILE = '/tmp/{}'.format(BUCKET_FILE_NAME)

    s3 = boto3.client('s3')

    try:
        s3.download_file(BUCKET_NAME, KEY, LOCAL_FILE)
        print("-=-= File 'structure.sql' downloaded -=-=-")
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("-=-=- The object does not exist. -=-=-=")
            failResponse("The object does not exist.")
        else:
            raise

def create_presigned_url():
    s3 = boto3.client('s3')

    try:
        response = s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': BUCKET_NAME,
                                                            'Key': BUCKET_FOLDER_PATH},
                                                    ExpiresIn=86400)
    except ClientError:
        print("-=-=- Wasn't able to generate presigned url to report file -=-=-")
        failResponse("Wasn't able to generate presigned url to report file.")

    # The response contains the presigned URL
    return response

def postBuild(presigned_url):
    TEAMCITY_URL = os.environ['TEAMCITY_URL']
    TEAMCITY_BUILD_ID = os.environ['TEAMCITY_BUILD_ID']
    TEAMCITY_TOKEN = os.environ['TEAMCITY_ACCESS_TOKEN']
    TEAMCITY_POST_URL = '{}/app/rest/buildQueue'.format(TEAMCITY_URL)
    TEAMCITY_REQUEST = {
          "buildType": {
            "id": TEAMCITY_BUILD_ID
          },
          "properties": {
            "property": [{
                "name": "teamcity.build.triggeredBy",
                "value": "AWS LAMBDA S3 EVENT"
              },
              {
                "name": "S3_CONFIG_FILE_URL",
                "value": presigned_url
              }
            ]
          }
    }

    TEAMCITY_HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": 'Bearer {}'.format(TEAMCITY_TOKEN)
    }

    try:
        print("-=- BEFORE MAKING CALL TO TEAMCITY -=-=-")

        response = requests.post(TEAMCITY_POST_URL, data=json.dumps(TEAMCITY_REQUEST), headers=TEAMCITY_HEADERS)
        response.raise_for_status()

        print(response)

    except requests.exceptions.HTTPError as error:
        print(error)
        failResponse("Error adding build config to queue in TeamCity.")

    print("-=- AFTER MAKING CALL TO TEAMCITY -=-=-")

def handler(event, context):
    print("-=-=-= GOT EVENT -=-=-=-")
    print(event)

    PRESIGNED_URL = create_presigned_url()
    postBuild(PRESIGNED_URL)

    body = {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "input": event
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response

    # Use this code if you don't use the http event with the LAMBDA-PROXY
    # integration
    """
    return {
        "message": "Go Serverless v1.0! Your function executed successfully!",
        "event": event
    }
    """
