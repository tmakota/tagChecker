import json
import logging
import boto3
import os


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


def handler(event, context):
    logger.info('## EVENT')
    logger.info(json.dumps(event))
    
    #Get instances with Owner Taggs and values Unknown/known
    instance_state = event["detail"]["state"]
    instance_id = event["detail"]["instance-id"]
    logger.info("Instance %s is in %s state", instance_id, instance_state)
    
    ec2instance = ec2.Instance(instance_id)
    instanceAppName = ''
    for tags in ec2instance.tags:
        if tags["Key"] == TAG_TO_VALIDATE:
            instanceAppName = tags["Value"]
            
    logger.info("Instance '%s', tag '%s' value is '%s'", instance_id, TAG_TO_VALIDATE, instanceAppName)
    
    if '' == instanceAppName :
        # check if this instance has already been flagged
        dynamodb.get_item(TableName=issues_table, Key={'instanceId':{'S':instance_id}})
    
    #dynamodb.put_item(TableName='fruitSalad', Item={'fruitName':{'S':'Banana'},'key2':{'N':'value2'}})