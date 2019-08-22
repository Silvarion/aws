import boto3
import json

# JSON structure expected
# {
#   "default": "<TARGET ARN TO PUBLISH TO>",
#   "attributes": {
#     "source": "<SOURCE RESOURCE/SERVICE FOR THE ALERT>",
#     "level": "<MESSAGE LEVEL = { NOTIFICATION | WARNING | ALERT | INCIDENT | CRITICAL }>",
#     "environment": "<ENVIRONMENT = { DEV | UAT | PRD }>"
#   },
#   "subject": "<MESSAGE SUBJECT>",
#   "text": "<MESSAGE TEXT>",
#   "slack": {
#     "channel": "<TARGET CHANNEL>",
#     "emoji_icon": "<ICON FOR THE MESSAGE SENDER>",
#     "color": "<COLOR FOR A LINE IN THE LEFT SIDE OF THE MESSAGE>", 
#     "attachments" = "<SLACK API COMPLIANT ATTACHMENTS LIST>"
#   },
#   "sns": {
#     "topic": "<TARGET TOPIC>",
#     "email_body": "<IF NOT PRESENT, text WILL BE USED INSTEAD>"
#   },
#   "ses": {
#     "source_email": "<EMAIL ADDRESS TO SEND EMAIL IN BEHALF OF>"
#   },
#   "elasticsearch": "<NOT IMPLEMENTED YET>"
# }

SNS_ARNS ={
  "<TARGET-SNS-TOPIC-1>": "<ENCRYPTED_ARN_1>",
  "<TARGET-SNS-TOPIC-2>": "<ENCRYPTED_ARN_2>",
  "<TARGET-SNS-TOPIC-3>": "<ENCRYPTED_ARN_3>"
}

def lambda_handler(event, context):
  print(event)
  # Create Lambda Client
  req_json = {
    "action": "decrypt",
    "message": SNS_ARNS[event['default']]
  }
  # Decrypt target SNS Topic
  client = boto3.client('lambda')
  resp_json = client.invoke(
    FunctionName = 'f-encrypt-decrypt',
    InvocationType = 'RequestResponse',
    LogType = 'None',
    Payload = bytes(json.dumps(req_json),'utf-8')
  )
  topic_arn = str(json.loads(resp_json['Payload'].read().decode())['body']).replace('"','')
  print(event)  
  client = boto3.client('sns')
  resp_json = client.publish(
    TargetArn = topic_arn,
    MessageStructure = 'String',
    Message = json.dumps(event),
    Subject = event['attributes']['level']['StringValue'] + " from " + event['attributes']['source']['StringValue'],
    MessageAttributes = event['attributes']
  )
  return {
    'statusCode': 200,
    'body': json.dumps(resp_json)
  }
