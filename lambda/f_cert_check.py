import boto3
import json
import datetime
from datetime import timedelta
import os

# Get Certificate Collection
def get_acm_expiring_certs():
  # Create ACM client
  acm = boto3.client('acm')
  # List certificates with the pagination interface
  paginator = acm.get_paginator('list_certificates')
  expiring_certs = {}
  for response in paginator.paginate():
    for certificate in response['CertificateSummaryList']:
      cert = acm.describe_certificate(CertificateArn=certificate['CertificateArn'])
      days_remaining = (cert['Certificate']['NotAfter'] - (datetime.datetime.now(datetime.timezone.utc))).days
      if  days_remaining < int(os.environ['DAYS_TO_EXPIRE']):
        expiring_certs[cert['Certificate']['DomainName']] = {
          'DomainName': cert['Certificate']['DomainName'],
          'CertificateArn': cert['Certificate']['CertificateArn'],
          'ExpirationDate': cert['Certificate']['NotAfter'],
          'RemainingDays': days_remaining
        }
  return expiring_certs

def get_txt(certs_dict):
  txt = ''
  txt += 'Expiring Certificates in AWS\n'
  txt += '============================\n'
  txt += '\n'
  for key in certs_dict.keys():
    txt += 'Domain Name: ' + certs_dict[key]['DomainName'] + '\n'
    txt += '\n'
    txt += 'Expiration Date: ' + certs_dict[key]['ExpirationDate'].strftime("%Y-%m-%d %H:%M:%S") + '\n'
    txt += '\n'
    txt += 'Days Remaining: ' + str(certs_dict[key]['RemainingDays']) + '\n'
    txt += '\n'
    txt += 'Certificate ARN: ' + certs_dict[key]['CertificateArn'] + '\n'
    txt += '\n'
    txt += '------------------------\n\n'
  return txt

def get_html(certs_dict):
  html = ''
  html += "<html>"
  html += '<h2>Expiring Certificates in AWS</h2><br/><br/>'
  html += '<table border="1"><tr><th>Certificate Domain</th><th>Expiration Date</th><th>Days Remaining</th><th>ARN</th></tr>'
  for key in certs_dict.keys():
    html += '<tr><td>'+ certs_dict[key]['DomainName'] +'</td><td>' + certs_dict[key]['ExpirationDate'].strftime("%Y-%m-%d %H:%M:%S") + '</td><td align="center">' + str(certs_dict[key]['RemainingDays']) + '</td><td>' + certs_dict[key]['CertificateArn'] + '</td></tr>'
  html += '</table>'
  html += '</html>'
  return html

def get_slack_blocks(certs_dict):
  blocks = []
  for key in certs_dict.keys():
    if certs_dict[key]['RemainingDays'] > 28:
      icon = ":warning:"
    elif certs_dict[key]['RemainingDays'] > 14:
      icon = ":rotating_light:"
    elif certs_dict[key]['RemainingDays'] > 7:
      icon = ":helmet_with_white_cross:"
    else:
      icon = ":negative_squared_cross_mark:"
    blocks.append(
      {
        "type": "section",
        "text": {
          "type": "plain_text",
          "text": icon + str(certs_dict[key]['DomainName'])
        }
      }
    )
    blocks.append(
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*Certificate ARN*: " + str(certs_dict[key]['CertificateArn'])
        }
      }
    )
    blocks.append(
      {
        "type": "section",
        "fields": [
          {
            "type": "mrkdwn",
            "text": "*Expiration Date*: " + certs_dict[key]['ExpirationDate'].strftime("%Y-%m-%d %H:%M:%S")
          },
          {
            "type": "mrkdwn",
            "text": "*Remaining Days*:" + str(certs_dict[key]['RemainingDays'])
          }
        ]
      }
    )
    blocks.append(

      {
        "type": "divider"
      }
    )
  return blocks
  

def get_slack_attachments(certs_dict):
  attachments = []
  for key in certs_dict.keys():
    if certs_dict[key]['RemainingDays'] > 28:
      attColor = "#28bf50"
    elif certs_dict[key]['RemainingDays'] > 14:
      attColor = "#ffeb14"
    elif certs_dict[key]['RemainingDays'] > 7:
      attColor = "#ff9114"
    else:
      attColor = "#ff1414"
    to_attach = {
      "fallback": "The " + certs_dict[key]['DomainName'] + " certificate expiring on AWS in " + str(certs_dict[key]['RemainingDays']) + " days",
      "pretext": certs_dict[key]['DomainName'],
      "color": attColor,
      "fields": [
        {
          "title": "ARN",
          "value": certs_dict[key]['CertificateArn'],
          "short": False
        },
        {
          "title": "Expiration Date",
          "value": certs_dict[key]['ExpirationDate'].strftime("%Y-%m-%d %H:%M:%S"),
          "short": True
        },
        {
          "title": "Remaining Days",
          "value": str(certs_dict[key]['RemainingDays']),
          "short": True
        }
      ]
    }
    attachments.append(to_attach)
  return attachments
    
def lambda_handler(event, context):
    # TODO implement
    expiring_certs = get_acm_expiring_certs()
    if len(expiring_certs) > 0:
      # html_body = get_html(expiring_certs)
      txt_body = get_txt(expiring_certs)
      #print(txt_body)
      
      sns = boto3.client('sns')
      json_msg = {}
      json_msg['default'] = "<TARGET-SNS-TOPIC>"
      json_msg['attributes'] = {
        "source": {
          "DataType": "String",
          "StringValue": "ACM"
        },
        "level": {
          "DataType": "String",
          "StringValue": "alert"
        }
      }
      json_msg['subject'] = 'Expiring certificates found in AWS ACM'
      json_msg['text'] = get_txt(expiring_certs)
      json_msg['slack'] = {}
      json_msg['slack']['channel'] = 'alerts-test'
      json_msg['slack']['username'] = 'AWS Global - Certificate Checker'
      json_msg['slack']['text'] = 'Expiring certificates found on ' + json_msg['attributes']['source']['StringValue']
      json_msg['slack']['blocks'] = get_slack_blocks(expiring_certs)
      json_msg['slack']['attachments'] = get_slack_attachments(expiring_certs)
      json_msg['sns'] = {}
      json_msg['sns']['topic'] = 'infrastructure_team'
      json_msg['sns']['email_body'] = get_txt(expiring_certs)
      print(json_msg)
      lambda_client = boto3.client('lambda')
      resp_json = lambda_client.invoke(
        FunctionName = 'f-publish-alert',
        InvocationType = 'Event',
        Payload = bytes(json.dumps(json_msg),'utf-8')
      )
      return {
        'statusCode': 200,
        'body': json.dumps('Expiring certificates notification sent!')
      }
    else:
      return {
        'statusCode': 200,
        'body': json.dumps('No expiring certificates found')
      }
