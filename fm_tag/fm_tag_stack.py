from typing import ValuesView
from aws_cdk import CfnOutput, CfnParameter, RemovalPolicy, Stack
from constructs import Construct
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_events_targets as e_targets
import aws_cdk.aws_events as events
import aws_cdk.aws_iam as iam

class FmTagStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB table to hold list of applications
        tag_issues_table = dynamodb.Table(self, "tag_issues_table",
                partition_key=dynamodb.Attribute(name="instanceId", type=dynamodb.AttributeType.STRING),
                removal_policy = RemovalPolicy.DESTROY
        )

        cmdb_apps_table = dynamodb.Table(self, "cmdb_apps_table",
                partition_key=dynamodb.Attribute(name="applicationId", type=dynamodb.AttributeType.STRING),
                removal_policy = RemovalPolicy.DESTROY
        )

        

        # create producer lambda function
        get_ec2_lambda = _lambda.Function(self, "producer_lambda_function",
                                              runtime=_lambda.Runtime.PYTHON_3_8,
                                              handler="lambda_function.handler",
                                              code=_lambda.Code.from_asset("./get_ec2_instances"))
        # set table names as parameters for Lambda function
        get_ec2_lambda.add_environment("ISSUES_TABLE", tag_issues_table.table_name)
        get_ec2_lambda.add_environment("CMDB_TABLE", cmdb_apps_table.table_name)

        # allow this lambda to invoke EC2 read only actions 
        get_ec2_lambda.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ReadOnlyAccess"))

        # grant permission to lambda to write to demo tables
        tag_issues_table.grant_read_write_data(get_ec2_lambda)
        cmdb_apps_table.grant_read_data(get_ec2_lambda)

        parm_default_bus_arn = "arn:aws:events:" + Stack.of(self).region + ":" +Stack.of(self).account +":event-bus/default"
        
        
        # create EventBus and 
        defaultBus = events.EventBus.from_event_bus_attributes(self, id="default", 
            event_bus_name="default",
            event_bus_arn=parm_default_bus_arn,
            event_bus_policy=""
        )

        bus =  events.EventBus(self, "fmTagsBus")
        CfnOutput(self, "fmTagsBusOutput", value= bus.event_bus_name)

        # event bus Rule
        events.Rule(self, "LambdaProcessorRule", 
                event_bus = defaultBus,
                event_pattern = events.EventPattern(
                    source =["aws.ec2"],
                    detail_type= ["EC2 Instance State-change Notification"],
                    detail = { "state" : ["running"]}
                ),
                targets = [ e_targets.LambdaFunction(get_ec2_lambda)]
        )
