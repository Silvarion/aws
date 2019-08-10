import boto3
import json
import base64
import urllib

SLACK_URLS = {
  'slack-incoming-webhook-1': 'EncryptedUrlHash',
}

SNS_ARNS = {
  'sns-topic-1': 'EncryptedArnHash'
}

def send_ses_email(payload):
  # Create SES client
  ses = boto3.client('ses')
  resp = ses.send_email(
    Source=payload['Source'],
    Destination=payload['Destination'],
    Message=payload['Message'],
    ReplyToAddresses=[
      'alerts@yourdomain.com',
    ],
    Tags=[
      {
        'Name': 'someKey',
        'Value': 'someValue'
      },
    ]
  )
  return resp

def send_slack_message(payload):
  # Get the right webhook
  HOOK_URL = 'https://' + boto3.client('kms').decrypt(CiphertextBlob=base64.b64decode(SLACK_URLS[payload['channel'].lower()]))['Plaintext'].decode("utf-8")
  req = urllib.request.Request(HOOK_URL, bytes(json.dumps(payload, default=str),'utf-8'), method='PUT')
  resp = urllib.request.urlopen(req)
  print("Message sent to Slack: ",resp)
  return resp

def publish_sns_topic(payload):
# Create an SNS client
  sns = boto3.client('sns')
# Publish a simple message to the specified SNS topic
  resp = sns.publish(
    TopicArn=boto3.client('kms').decrypt(CiphertextBlob=base64.b64decode(SNS_ARNS[payload['topic'].lower()]))['Plaintext'].decode("utf-8"),
    Message=payload['message']
  )
  # Print out the response
  return resp

### Main function handler ###
def lambda_handler(event, context):
  print(event)
  result = {}
  for target in event.keys():
    if target == 'slack':
      response = send_slack_message(event[target])
      decoded_resp = response.read().decode("utf-8")
      if decoded_resp == 'ok':
        result[target] = "Sent Slack message\n"
      else:
        result[target] = "Slack message failed\n HTTP response: " + decoded_resp 
    elif target == 'sns':
      response = publish_sns_topic(event[target])
      print(response.keys())
      if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        result[target] = "Published SNS message\n"
      else:
        result[target] = "SNS message failed\n HTTP response: " + str(response['ResponseMetadata']['HTTPStatusCode'])
    elif target == 'ses':
      response = send_ses_email(event[target])
      result[target] = "Sent SES email\n"
    else:
      result[target] = "Unrecognized target " + target + "!!!"
  return {
    'statusCode': 200,
    'body': json.dumps(result)
  }
