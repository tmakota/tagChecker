import json
import logging
import boto3
import os
from botocore.exceptions import ClientError

cmdb_table = os.environ['CMDB_TABLE']
issues_table = os.environ['ISSUES_TABLE']
  
ec2 = boto3.resource('ec2')
dynamodb = boto3.client('dynamodb')

TAG_TO_VALIDATE ="AppName"

# also see these blog
# https://aws.amazon.com/blogs/mt/monitor-tag-changes-on-aws-resources-with-serverless-workflows-and-amazon-cloudwatch-events/
# https://aws.amazon.com/blogs/mt/auto-tag-aws-resources/


# sample event
# {
#    "version": "0",
#    "id": "64c8a3ff-e7b3-a6f8-e74a-08306b6a467a",
#    "detail-type": "EC2 Instance State-change Notification",
#    "source": "aws.ec2",
#    "account": "107764952090",
#    "time": "2021-06-05T13:37:48Z",
#    "region": "us-east-1",
#    "resources": [
#        "arn:aws:ec2:us-east-1:107764952090:instance/i-011d60cd552f7289b"
#    ],
#    "detail": {
#        "instance-id": "i-011d60cd552f7289b",
#        "state": "running"
#    }
# }


logger = logging.getLogger()
logger.setLevel(logging.INFO)

#===========================================================================
# issue_exists
#===========================================================================
def issue_exists(instanceId, dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table(issues_table)

    try:
        response = table.get_item(Key={'instanceId':instanceId})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        logger.info("issue_exists('%s'), returning '%s' ", instanceId, json.dumps(response['Item']))
        
    return "Item" in response

#===========================================================================
# create_new_issue
#===========================================================================
def create_new_issue(ec2Instance, keyName, issueDescription, dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table(issues_table)
    
    response = table.put_item(
       Item={
            'instanceId': ec2Instance.instance_id,
            'instance_type': ec2Instance.instance_type,
            'vpc_id' : ec2Instance.vpc_id,
            'launch_time' : ec2Instance.launch_time.strftime("%m/%d/%Y, %H:%M:%S"),
            'keyName': keyName,
            'issueDescription' : issueDescription
        }
    )
    return response

#===========================================================================
# check_tag_cmdb_value
#===========================================================================
def check_tag_cmdb_value(tagValue, dynamodb=None):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table(cmdb_table)

    try:
        response = table.get_item(Key={'applicationId':tagValue})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        logger.info("check_tag_cmdb_value('%s'), returning '%s' ", tagValue, json.dumps(response))
        
        return "Item" in response
    
def handler(event, context):
    logger.info('## EVENT')
    logger.info(json.dumps(event))
    
    #Get instances with Owner Taggs and values Unknown/known
    instance_state = event["detail"]["state"]
    instance_id = event["detail"]["instance-id"]
    logger.info("Instance %s is in %s state", instance_id, instance_state)
    
    ec2instance = ec2.Instance(instance_id)
    instanceAppId = ''
    for tags in ec2instance.tags:
        if tags["Key"] == TAG_TO_VALIDATE:
            instanceAppId = tags["Value"]
            
    logger.info("Instance '%s', tag '%s' value is '%s'", instance_id, TAG_TO_VALIDATE, instanceAppId)
    
    issueDescription = ""
    if '' == instanceAppId :
        issueDescription = "Value of the tag '" + TAG_TO_VALIDATE +"' is '" + instanceAppId +"' [EMPTY]."
    else:
        cmdbResponse = check_tag_cmdb_value(instanceAppId)
        if cmdbResponse :
            logger.info("No Actions Required: instance %s has tag value of %s which is valid AppName", instance_id, instanceAppId)
            return
        else:
            issueDescription = "Value of the tag '" + TAG_TO_VALIDATE +"' is '" + instanceAppId +"' but its not present in CMDB table."
            logger.info("check_tag_cmdb_value returned %s", cmdbResponse)
        
    
    logger.info("Instance doesnt have correct tag value, recording it in issues table ")
    create_new_issue(ec2instance, TAG_TO_VALIDATE, issueDescription)
    
   