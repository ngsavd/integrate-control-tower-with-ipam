import json
import os
import boto3
import botocore.exceptions
from netaddr import *
import decimal
from datetime import datetime
import time
import logging
import random
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
client = boto3.client('ec2')

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

def returnAvailableSubnet(supernetSet, usedSubnets, subnetPrefix, Region):
    totalIps = supernetSet.size
    findAvailableSubnets(supernetSet, usedSubnets)
    freeSubnets = []
    for network in supernetSet.iter_cidrs():
        newNetwork = IPNetwork(network)
        subnets = list(newNetwork.subnet(subnetPrefix))
        for subnet in subnets:
            freeSubnets.append(subnet)
    totalFreeIps = IPSet(freeSubnets).size
#    monitoring(totalIps, totalFreeIps, Region, Env)
    if len(freeSubnets) > 0:
        return freeSubnets[0]
    else:
        raise LookupError('no avaialble subets for this region and environment')

def sendResponse(event, context, responseStatus, responseData):
    responseBody = {'Status': responseStatus,
                    'Reason': 'See the details in CloudWatch Log Stream: ' + context.log_stream_name,
                    'PhysicalResourceId': context.log_stream_name,
                    'StackId': event['StackId'],
                    'RequestId': event['RequestId'],
                    'LogicalResourceId': event['LogicalResourceId'],
                    'Data': responseData}
    print('RESPONSE BODY:n' + json.dumps(responseBody))
    try:
        req = requests.put(event['ResponseURL'], data=json.dumps(responseBody))
        if req.status_code != 200:
            print(req.text)
            raise Exception('Recieved non 200 response while sending response to CFN.')
        return
    except requests.exceptions.RequestException as e:
        print(e)
        raise


def handler(event, context):
    print("REQUEST RECEIVED")
    print(event)
    usedSubnets = []
    regionalUsedSubnets = []
    supernets = []
    supernets.append(event['ResourceProperties']['TopLevelPoolCidr']);
    supernetSet = IPSet(supernets)
    prefix = int(os.environ['IPAM_POOL_PREFIX'])
    Region = os.environ['IPAM_REGION']
    ipam_scope = os.environ['IPAM_SCOPE']
    #AccEnvName = os.environ['AccEnvName']
    AccPoolPrefixLength = int(os.environ['AccPoolPrefixLength'])
    
    

    poolRegions = event['ResourceProperties']['IpamPoolRegions']
    AccEnvName = event['ResourceProperties']['AccEnvName']
    print(poolRegions)
    print(AccEnvName)

    if event.get('RequestType') == 'Create':
      for poolRegion in poolRegions:
        print(supernetSet)
        print(prefix)
        cidrToAssign = str(returnAvailableSubnet(supernetSet, usedSubnets, prefix, Region))
        print("creating pool for region=" + poolRegion )
        response = client.create_ipam_pool(
        IpamScopeId=os.environ['IPAM_SCOPE'],Locale=poolRegion,SourceIpamPoolId=event['ResourceProperties']['TopLevelPool'],AddressFamily='ipv4')
        memberIpamPoolId = response['IpamPool']['IpamPoolId']
        ipamPoolArn = response['IpamPool']['IpamPoolArn'] 
        print("Response from create ipam pool1" + memberIpamPoolId)
        time.sleep(30)
        response = client.describe_ipam_pools(
        IpamPoolIds=[
            memberIpamPoolId
        ]
        )
        print(response)
        
        print("We will assign Cidr")
        print(cidrToAssign)
        usedSubnets.append(cidrToAssign)
        response = client.provision_ipam_pool_cidr(IpamPoolId=memberIpamPoolId,Cidr=cidrToAssign)
    
            # Now Create Environment Level pools
        for EachAccEnvName in AccEnvName:
            regionalSupernets = []
            regionalSupernets.append(cidrToAssign);
            regionalSupernetSet = IPSet(regionalSupernets)
            envCidrToAssign = str(returnAvailableSubnet(regionalSupernetSet, regionalUsedSubnets, AccPoolPrefixLength , Region))
            print("creating Prod Env pool for region=" + poolRegion )
            print(envCidrToAssign);
            response = client.create_ipam_pool(
            IpamScopeId=os.environ['IPAM_SCOPE'],Locale=poolRegion,SourceIpamPoolId=memberIpamPoolId,AddressFamily='ipv4',AllocationResourceTags=[{'Key':'Env','Value': EachAccEnvName}])
            envIpamPoolId = response['IpamPool']['IpamPoolId']
            ipamPoolArn = response['IpamPool']['IpamPoolArn'] 
            print("Response from create ipam pool2" + envIpamPoolId)
            time.sleep(30)
            response = client.describe_ipam_pools(
            IpamPoolIds=[
                envIpamPoolId
            ]
            )
            print(response)
            regionalUsedSubnets.append(envCidrToAssign)
            response = client.provision_ipam_pool_cidr(IpamPoolId=envIpamPoolId,Cidr=envCidrToAssign)
            print(response)
      responseData = {}
      responseStatus = 'SUCCESS'
      responseData['message'] = "Goodbye from lambda from create"
      logging.info('Sending %s to cloudformation', responseData['message'])        
      sendResponse(event, context, responseStatus, responseData)
    elif event.get('RequestType') == 'Delete':
      responseData = {}
      responseStatus = 'SUCCESS'
      responseData['message'] = "Goodbye from lambda"
      logging.info('Sending %s to cloudformation', responseData['message'])
      sendResponse(event, context, responseStatus, responseData)
    else:
      logging.error('Unknown operation: %s', event.get('RequestType'))
