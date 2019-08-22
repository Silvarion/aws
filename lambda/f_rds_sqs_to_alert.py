import boto3
import json


SLACK_DEFAULT_ICONS = {
  "notification": ":information_source:",
  "warning": ":warning:",
  "alert": ":rotating_light:",
  "incident": ":helmet_with_white_cross:",
  "critical": ":negative_squared_cross_mark:",
  "other": ":eyes:"
}

def parse_sqs_message(payload):
  # Dictionarize the message body
  body = json.loads(str(payload["body"]).replace("'",'"'))
  # print(body)
  if str(body['Type']).lower() in SLACK_DEFAULT_ICONS.keys():
    icon = SLACK_DEFAULT_ICONS[str(body['Type']).lower()]
  # Override icon depending on the message
    # Database Failover
  elif str(body["Message"]).find('failover') != -1:
    icon = SLACK_DEFAULT_ICONS['incident']
    # Database shutdown
  elif str(body["Message"]).find('shutdown') != -1:
    icon = SLACK_DEFAULT_ICONS['incident']
    # RDS Object Creation
  elif str(body["Message"]).find('creat') != -1:
    icon = SLACK_DEFAULT_ICONS['warning']
    # RDS Object Deletion
  elif str(body["Message"]).find('delet') != -1:
    icon = SLACK_DEFAULT_ICONS['warning']
  else:
    icon = ":eyes:"
  # Check if the message is a JSON structure
  if str(body["Message"]).find("{") != -1:
    message = json.loads(body["Message"])
    # Read relevant elements
    if 'Event Source' in message.keys():
      event_source = message['Event Source']
    else:
      event_source = 'RDS'
    if 'Source ID' in message.keys():
      event_source_id = message['Source ID']
    else:
      event_source_id = 'RDS'
    if 'Event ID' in message.keys():
      event_id = message['Event ID']
    elif 'Identifier Link' in message.keys():
      event_id = message['Identifier Link']
    else: 
      event_id = '_<No Links provided>_'
    if 'Event Time' in message.keys():
      event_time = message['Event Time']
    else:
      event_time = message['Timestamp']
    # Create the payload
    payload = {
      'default': '<TARGET-SNS-TOPIC>',
      'attributes': {
        "source": {
          "DataType": "String",
          "StringValue": "RDS"
        },
        "level": {
          "DataType": "String",
          "StringValue": str(body['Type']).lower()
        },
        'environment': {
          "DataType": "String",
          "StringValue": "N/A"
        }
      },
      'subject': body['Subject'],
      'text': body['Message'],
      'slack': {
        'channel': 'alerts-test',
        'username': 'AWS China - RDS Monitor',
        'blocks': [
          {
            "type": "section",
            "text": {
              "type": "plain_text",
              "text": body['Type'] + " from " + event_source + ":",
              "emoji": True
            }
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": icon + "*Event*: " + message['Event Message']
            }
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Resource*: " + event_source_id
            }
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Time*: " + event_time
            }
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Event ID*: " + event_id
            }
          },
          {
            "type": "divider"
          }
        ]
      }
    }

  else:
    payload = {
      'default': '<TARGET-SNS-TOPIC>',
      'attributes': {
        "source": {
          "DataType": "String",
          "StringValue": "RDS"
        },
        "level": {
          "DataType": "String",
          "StringValue": str(body['Type']).lower()
        },
        'environment': {
          "DataType": "String",
          "StringValue": "N/A"
        }
      },
      'subject': body['Subject'],
      'text': body['Message'],
      'slack': {
        'channel': 'alerts-test',
        'username': 'AWS China'
      }
    }
  return payload

def lambda_handler(event, context):
  print(event)
  for record in event['Records']:
    alert_payload = parse_sqs_message(record)
    # print(alert_payload)
    # Send the actual alert
    lambda_client = boto3.client('lambda')
    lambda_client.invoke(
      FunctionName = 'f-publish-alert',
      InvocationType = 'Event',
      LogType = 'None',
      Payload = bytes(json.dumps(alert_payload),'utf-8')
    )
  return {
    'statusCode': 200,
    'body': json.dumps(event['Records'])
  }
