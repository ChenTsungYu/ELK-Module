"""
(終版) 平行處理
describe-instances doc:
https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-instances.html
https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeInstances.html
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances
Fields:
Instance ID, Instance Type, Operating System, Subnet, Availability zone, 
Private IP, Public IP, Public DNS, Key Name, Security groups
"""
import subprocess, json, shlex, pytz, time, itertools
from datetime import datetime
from elasticsearch import Elasticsearch
from multiprocessing import Process, Pool 
from regions_list import regions, region_list
from secret import ElasticAccount, ElasticHost, ElasticPassword
from auth import listProfiles
es = Elasticsearch( # Cloud version
    cloud_id=f"{ElasticHost}",
    http_auth=(f"{ElasticAccount}", f"{ElasticPassword}"),
)
def main(params): 
    profile = params[0]
    region = params[1]
    jData = []
    try:
        resources_list_command = f"aws ec2 describe-instances --profile {profile} --query Reservations[*].Instances[*] --region {region} --output json"
        resources_output = subprocess.check_output(shlex.split(resources_list_command))
        jData = json.loads(resources_output)
    except Exception as e:
        # print(f"region: {region} is't been set")
        pass
    for instance in jData:
        for item in instance:
            item["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            item["AccountName"] = profile
            item["Region"] = region
            item["RegionName"] = region_list[region]
            instance_sgs = [groupNames['GroupName'] for groupNames in item['SecurityGroups']]
            item['SecurityGroups'] = 'None' if instance_sgs == [] else ", ".join(instance_sgs)
            try:
                item["InstanceName"] = [tag['Value'] for tag in item['Tags'] if "Name" == tag["Key"]][0]
            except Exception as e:
                # print(f"region: {region}; profile: {profile}; There isn't any tag in this instance: {item['InstanceId']}")
                item["InstanceName"] = "-"
            # print("instance: ", item)
            es.index(index='aws-resource-ec2', body=json.dumps(item))

starttime = time.time()
profiles = listProfiles()
paramlist = list(itertools.product(profiles, regions))
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main,paramlist)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)