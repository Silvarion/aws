import boto3
import json

def lambda_handler(event, context):
  print(event)
  for record in event['Records']:
    msg_json = json.loads(json.loads(record['body'])['Message'])
    lambda_client = boto3.client('lambda')
    #print(json.dumps(msg_json))
    # Send the actual alert
    #print('Invocation with:\n' + json.dumps(msg_json))
    lambda_client.invoke(
      FunctionName = 'f-send-alert',
      InvocationType = 'Event',
      LogType = 'None',
      Payload = bytes(json.dumps(msg_json),'utf-8')
    )
    sqs = boto3.client('sqs')
    split_arn = record['eventSourceARN'].split(':')
    queue_url = sqs.get_queue_url(
      QueueName = split_arn[len(split_arn) - 1],
      QueueOwnerAWSAccountId = split_arn[len(split_arn) - 2]
      )['QueueUrl']
    sqs.delete_message(
      QueueUrl = queue_url,
      ReceiptHandle = record['receiptHandle']
      )
  return {
    'statusCode': 200,
    'body': json.dumps(event['Records'])
  }
