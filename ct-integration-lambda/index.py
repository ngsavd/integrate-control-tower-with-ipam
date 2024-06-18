import json
import os
import boto3
import botocore.exceptions
from boto3.dynamodb.conditions import Attr 
from netaddr import *
import decimal
from datetime import datetime
import time

sts_connection = boto3.client('sts')
organizations = boto3.client('organizations')
ec2 = boto3.resource('ec2')
snsTopic = os.environ['SNS_TOPIC']
snsClient = boto3.client('sns')


def findAvailableSubnets(supernetSet, usedSubnets):
    for subnet in usedSubnets:
        supernetSet.remove(subnet)
    return supernetSet
    
def alert(percentageUsed, Region, Env):
    response = snsClient.publish(
        TopicArn=snsTopic,
        Message='WARNING: ' + Env + ' in region ' + Region + ' has used ' + str(percentageUsed) + '% of available CIDR addresses',
        Subject='WARNING free CIDR ranges running low',
    )
    print(response)
    print('alert')
    return response
    
def monitoring(supernetSet, freeSubnets, Region, Env):
    percentageUsed = int(100-((freeSubnets/supernetSet)*100))
    if percentageUsed > 80:
        alert(percentageUsed, Region, Env)
        return
    else:
        return

def returnAvailableSubnet(supernetSet, usedSubnets, subnetPrefix, Region, Env):
    totalIps = supernetSet.size
    findAvailableSubnets(supernetSet, usedSubnets)
    freeSubnets = []
    for network in supernetSet.iter_cidrs():
        newNetwork = IPNetwork(network)
        subnets = list(newNetwork.subnet(subnetPrefix))
        for subnet in subnets:
            freeSubnets.append(subnet)
    totalFreeIps = IPSet(freeSubnets).size
    monitoring(totalIps, totalFreeIps, Region, Env)
    if len(freeSubnets) > 0:
        return freeSubnets[0]
    else:
        raise LookupError('no avaialble subets for this region and environment')
    

def getUsedCidrs(Region, Env):
    usedSubnets = []
    Records = scanDDB(table, Region=Region, Env=Env)
    for Record in Records['Items']:
        usedSubnets.append(Record['Cidr'])
        while 'LastEvaluatedKey' in Records:
            Records = scanDDB(table, LastEvaluatedKey=Records['LastEvaluatedKey'], Region=Region, Env=Env)
            for Record in Records['Items']:
                usedSubnets.append(Record['Cidr'])
    return usedSubnets

def lambda_handler(event, context):
    print(event)
    prefix = int(os.environ['IPAM_POOL_PREFIX'])
    childAccountId = int(event['detail']['serviceEventDetails']['createManagedAccountStatus']['account']['accountId'])
    childAccountName = event['detail']['serviceEventDetails']['createManagedAccountStatus']['account']['accountName']
    TagValue=event['detail']['serviceEventDetails']['createManagedAccountStatus']['organizationalUnit']['organizationalUnitName']
    Region = os.environ['IPAM_REGION']
    ipam_scope = os.environ['IPAM_SCOPE']
    
    networkAccountCredentials = sts_connection.assume_role(RoleArn=os.environ['EXECUTION_ROLE_ARN'],RoleSessionName='ControlTowerExecutionRoleSession')
    ACCESS_KEY = networkAccountCredentials['Credentials']['AccessKeyId']
    SECRET_KEY = networkAccountCredentials['Credentials']['SecretAccessKey']
    SESSION_TOKEN = networkAccountCredentials['Credentials']['SessionToken']

    networkAccountEC2Client= boto3.client(
        'ec2',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )


    response= networkAccountEC2Client.describe_ipam_pools()
    memberIpamPoolArn =[]
    AllocationResourceTags=[]
    for pool in response['IpamPools']:
        print(pool['IpamPoolId'])
        if 'AllocationResourceTags' in pool:
            for tag in pool['AllocationResourceTags']:
                if tag['Key'] == 'Env' and tag['Value'] == TagValue :
                    print("selected pool " + pool['IpamPoolId'])
                    memberIpamPoolArn.append(pool['IpamPoolArn'])
   
    print("memberIpamPoolArn: " + str(memberIpamPoolArn))
    networkAccountRAMClient= boto3.client(
        'ram',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN,
    )
    response = networkAccountRAMClient.create_resource_share(
        name='ipamShare-'+ str(childAccountId),
        resourceArns=memberIpamPoolArn,
        principals=[
            str(childAccountId)
        ],
    )
    
    response = {
                'isBase64Encoded': False,
                'statusCode': 200,
                'headers': {},
                'multiValueHeaders': {},
                'body': '{"statusMessage": "' + response['resourceShare']['status'] + '" }'
            }
    return response
