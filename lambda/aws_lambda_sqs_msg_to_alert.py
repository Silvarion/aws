import boto3
import json

def parse_sqs_message(payload,response_json):
  # Initialize variables
  alert_json = response_json
  body_dict = json.loads(payload['body'])
  if str(body_dict['Subject']).lower().find('fail') != -1 or str(body_dict['Subject']).lower().find('shutdown')  != -1 or str(body_dict['Subject']).lower().find('restart')  != -1:
    attColor = "#ff1414"
  elif str(body_dict['Message']).lower().find('fail') != -1 or str(body_dict['Message']).lower().find('shutdown')  != -1 or str(body_dict['Message']).lower().find('restart')  != -1:
    attColor = "#ff1414"
  else:
    attColor = "#28bf50"
  if str(payload['eventSourceARN']).find("sqs-queue-1") > 0:
    event_source = "Some nice source name 1"
  elif str(payload['eventSourceARN']).find("sqs-queue-2") > 0:
    event_source = "Some nice source name 2"
  else:
    event_source = ">> Unknown <<"
    
  alert_json['slack']['attachments'].append(
    {
      "fallback": "Message from "+ event_source +" Notifications in AWS China: " + "[" + str(body_dict['Timestamp']).replace('T',' ') + "]"  + body_dict['Subject'] + " -> " + body_dict['Message'],
      "pretext": body_dict['Type'],
      "color": attColor,
      "fields": [
        {
          "title": "Subject",
          "value": body_dict['Subject'],
          "short": True
        },
        {
          "title": "Timestamp",
          "value": body_dict['Timestamp'],
          "short": True
        },
        {
          "title": "Message",
          "value": body_dict['Message'],
          "short": False
        }
      ]
    }
  )
  return alert_json

def lambda_handler(event, context):
  response_json = {}
  response_json ['slack'] = {
		"channel": "your-target-slack-channel",
		"text": "Your custom text for alerts or notifications",
		"username": "Some nice username or title for the posts",
		"icon_emoji": ":warning:",
    "attachments": []
	}

  for record in event['Records']:
    response_json = parse_sqs_message(record,response_json)

  # Send the actual alert
  lambda_client = boto3.client('lambda')
  lambda_client.invoke(
    FunctionName = 'lambda-send-alert',
    InvocationType = 'Event',
    LogType = 'None',
    Payload = bytes(json.dumps(response_json),'utf-8')
  )
  return {
    'statusCode': 200,
    'body': json.dumps(event['Records'])
  }
