import boto3
import json
import base64
from urllib import request

SLACK_URLS = {
  'slack-channel-1': '<ENCRYPTED_WEBHOOK_URL_1>',
  'slack-channel-2': '<ENCRYPTED_WEBHOOK_URL_2>',
  'slack-channel-3': '<ENCRYPTED_WEBHOOK_URL_3>',
  'slack-channel-4': '<ENCRYPTED_WEBHOOK_URL_4>'
}

SNS_ARNS = {
  'sns-endpoint-1': '<SNS_ARN_FOR_EMAIL_SMS_PUSH_NOTIFICATIONS_1>',
  'sns-endpoint-2': '<SNS_ARN_FOR_EMAIL_SMS_PUSH_NOTIFICATIONS_2>',
  'sns-endpoint-3': '<SNS_ARN_FOR_EMAIL_SMS_PUSH_NOTIFICATIONS_3>',
  'sns-endpoint-4': '<SNS_ARN_FOR_EMAIL_SMS_PUSH_NOTIFICATIONS_4>'
}

SLACK_DEFAULT_ICONS = {
  "notification": ":information_source:",
  "warning": ":warning:",
  "alert": ":rotating_light:",
  "incident": ":helmet_with_white_cross:",
  "critical": ":negative_squared_cross_mark:"
}

def send_ses_email(payload):
  # Create SES client
  ses = boto3.client('ses')
  resp = ses.send_email(
    Source=payload['Source'],
    Destination=payload['Destination'],
    Message=payload['Message'],
    ReplyToAddresses=[
      '<REPLY_TO_ADDRESS>',
    ],
    Tags=[
      {
        'Name': 'owner',
        'Value': 'upc'
      },
    ]
  )
  print(resp)
  return resp

def send_slack_message(payload):
  # Decrypt target channel URL
  client = boto3.client('lambda')
  req_json = {
    "action": "decrypt",
    "message": SLACK_URLS[str(payload['slack']['channel']).lower()]
  }
  resp_json = client.invoke(
    FunctionName = 'f-encrypt-decrypt',
    InvocationType = 'RequestResponse',
    LogType = 'None',
    Payload = bytes(json.dumps(req_json),'utf-8')
  )
  channel_url = 'https://' + str(json.loads(resp_json['Payload'].read().decode())['body']).replace('"','')
  print(channel_url)
  # Build the SLACK Payload
  slack_payload = {}
  # slack_payload["channel"] = channel_url
  if "text" in payload["slack"].keys():
    slack_payload["text"] = payload["slack"]["text"]
  else:
    slack_payload["text"] = payload["text"]
  if "username" in payload["slack"].keys():
    slack_payload["username"] = payload["slack"]["username"]
  else:
    slack_payload["username"] = 'AWS ' + str(payload["attributes"]["level"]['StringValue']).capitalize()
  if "icon_emoji" in payload["slack"].keys():
    slack_payload["icon_emoji"] = payload["slack"]["icon_emoji"] 
  else:
    slack_payload["icon_emoji"] = SLACK_DEFAULT_ICONS[str(payload["attributes"]["level"]['StringValue']).lower()]
  if "attachments" in payload["slack"].keys():
    slack_payload["attachments"] = payload["slack"]["attachments"]
  if "blocks" in payload["slack"].keys():
    slack_payload["blocks"] = payload["slack"]["blocks"]
  print(slack_payload)
  try:
    req = request.Request(channel_url, bytes(json.dumps(slack_payload, default=str),'utf-8'), method='PUT')
    resp = request.urlopen(req)
    decoded_resp = resp.read().decode("utf-8")
    print("Message sent to Slack: ",decoded_resp)
  except Exception as e:
    print("ERROR while sending SLACK message")
    print(e.__str__)
    decoded_resp = "error"
  return decoded_resp

def publish_sns_topic(payload):
  # Decrypt target topic ARN
  client = boto3.client('lambda')
  req_json = {
    "action": "decrypt",
    "message": SNS_ARNS[payload['sns']['topic'].lower()]
  }
  resp_json = client.invoke(
    FunctionName = 'f-encrypt-decrypt',
    InvocationType = 'RequestResponse',
    LogType = 'None',
    Payload = bytes(json.dumps(req_json),'utf-8')
  )
  topic_arn = str(json.loads(resp_json['Payload'].read().decode())['body']).replace('"','')
  print('Topic ARN: ' + topic_arn)
  # Check for email_body in SNS
  if 'email_body' in payload['sns'].keys():
    sns_msg=payload['sns']['email_body']
  else:
    sns_msg=payload['text']
# Create an SNS client
  sns = boto3.client('sns')
# Publish a simple message to the specified SNS topic
  resp = sns.publish(
    TopicArn=topic_arn,
    Subject=payload['subject'],
    MessageStructure = 'String',
    Message=sns_msg
  )
  # Print out the response
  print('SNS Message published\n' + resp)
  return resp

### Main function handler ###
def lambda_handler(event, context):
  print(event)
  payload = event
  result = {}
  for target in payload.keys():
  # Process SLACK payload items
    if target == 'slack':
      response = send_slack_message(event)
      if response == 'ok':
        result[target] = "Sent Slack message\n"
      else:
        result[target] = "Slack message failed\n HTTP response: " + response 
    elif target == 'sns':
      response = publish_sns_topic(event)
      print(response.keys())
      if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        result[target] = "Published SNS message\n"
      else:
        result[target] = "SNS message failed\n HTTP response: " + str(response['ResponseMetadata']['HTTPStatusCode'])
    elif target == 'ses':
      response = send_ses_email(event)
      result[target] = "Sent SES email\n"
    else:
      result[target] = "Unrecognized target " + target + "!!!"
  return {
    'statusCode': 200,
    'body': json.dumps(result)
  }
