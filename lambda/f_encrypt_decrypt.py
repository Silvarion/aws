import boto3
import json
import base64

def encrypt(string):
  kms = boto3.client('kms')
  response = kms.encrypt(
      KeyId='<KMS_KEY_ARN>',
      Plaintext=bytes(string, 'utf-8')
  )
  binary_encrypted = response[u'CiphertextBlob']
  encrypted_bytes = base64.b64encode(binary_encrypted)
  encrypted_string = encrypted_bytes.decode()
  return(encrypted_string)

def decrypt(byte_array):
  kms = boto3.client('kms')
  response = kms.decrypt(
    CiphertextBlob=base64.b64decode(byte_array)
  )
  decrypted_string = response['Plaintext']
  return(decrypted_string.decode())

def lambda_handler(event, context):
  if event['action'].lower() == 'encrypt':
    result = encrypt(event['message'])
  elif event['action'].lower() == 'decrypt':
    result = decrypt(event['message'])
  return {
      'statusCode': 200,
      'body': json.dumps(result)
  }
