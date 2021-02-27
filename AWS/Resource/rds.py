"""
(終版)
API Doc:
https://docs.aws.amazon.com/cli/latest/reference/rds/describe-db-instances.html
Fields:
DB identifier, Instance Type, DB Name, Endpoint, 
DB Engine version, Availability zone, VPC, Subnets, VPC security groups
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
        resources_list_command = f"aws rds describe-db-instances --profile {profile}  --region {region} --output json"
        resources_output = subprocess.check_output(shlex.split(resources_list_command))  
        jData = json.loads(resources_output)
    except Exception as e:
        # print(f"region: {region} is't been set")
        pass
    if len(jData) != 0:
        for instance in jData['DBInstances']:
            print("region: ", region)
            instance["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            instance["AccountName"] = profile
            instance["Region"] = region
            instance["RegionName"] = region_list[region]
            instance['InstanceCreateTime'] = instance['InstanceCreateTime']
            subnets = [ subnets["SubnetIdentifier"] for subnets in instance['DBSubnetGroup']["Subnets"] ]
            instance['subnetsIDs'] = 'None' if subnets == [] else ", ".join(subnets)
            # print(instance)
            es.index(index='aws-resource-rds', body=json.dumps(instance))

starttime = time.time()
profiles = listProfiles()
paramlist = list(itertools.product(profiles, regions))
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, paramlist)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)