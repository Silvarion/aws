import boto3
import json
import datetime
from datetime import timedelta
import os
import urllib

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

def get_html(certs_dict):
  html = "<html>"
  html += '<h2>Expiring Certificates in AWS</h2><br/><br/>'
  html += '<table border="1"><tr><th>Certificate Domain</th><th>Expiration Date</th><th>Days Remaining</th><th>ARN</th></tr>'
  for key in certs_dict.keys():
    html += '<tr><td>'+ certs_dict[key]['DomainName'] +'</td><td>' + certs_dict[key]['ExpirationDate'].strftime("%Y-%m-%d %H:%M:%S") + '</td><td align="center">' + str(certs_dict[key]['RemainingDays']) + '</td><td>' + certs_dict[key]['CertificateArn'] + '</td></tr>'
  html += '</table></html>'
  return html

def send_email(certs_dict):
  # Create SES client
  
  email_body = get_html(certs_dict)
  ses_payload = {
    'ses': {
      'Source': 'UplayPCInfrastructureTeam@ubisoft.com',
      'Destination': {
        'ToAddresses': [
          'UplayPCInfrastructureTeam@ubisoft.com',
        ]
      },
      'Message': {
        'Subject': {
          'Data': '[REPORT] Expiring Certificates in AWS',
          'Charset': 'UTF8'
        },
        'Body': {
          'Html': {
            'Data': email_body,
            'Charset': 'UTF8'
          }
        }
      },
      'ReplyToAddresses': [
        'UplayPCInfrastructureTeam@ubisoft.com',
      ],
      'Tags': [
        {
          'Name': 'owner',
          'Value': 'upc'
        },
      ],
    }
  }
  return ses_payload

def send_slack_notification(certs_dict):
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
      "fallback": "The " + certs_dict[key]['DomainName'] + "certificate expiring on AWS in " + str(certs_dict[key]['RemainingDays']) + " days",
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
          "value": certs_dict[key]['ExpirationDate'],
          "short": True
        },
        {
          "title": "Remaining Days",
          "value": certs_dict[key]['RemainingDays'],
          "short": True
        }
      ]
    }
    attachments.append(to_attach)
  slack_payload = {
    'slack': {
      'channel': 'infrastructure',
      'text': 'Expiring certificates found in AWS ACM',
      'username': 'AWS Global',
      'icon_emoji': ':warning:',
      'attachments': attachments
    }
  }
  return slack_payload
    
   
def lambda_handler(event, context):
    # TODO implement
    expiring_certs = get_acm_expiring_certs()
    if len(expiring_certs) > 0:
      full_payload = {}
      full_payload['ses'] = send_email(expiring_certs)
      full_payload['slack'] = send_slack_notification(expiring_certs)
      lambda_client = boto3.client('lambda')
      lambda_client.invoke(
        FunctionName = 'upcSendAlert',
        InvocationType = 'Event',
        LogType = 'None',
        Payload = bytes(json.dumps(full_payload),'utf-8')
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
