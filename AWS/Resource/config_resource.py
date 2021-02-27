"""
(終版)
configservice doc:
https://docs.aws.amazon.com/cli/latest/reference/configservice/index.html
盤點各Region 下的數量
"""
import subprocess, json, shlex, pytz, time, itertools
from datetime import datetime
from elasticsearch import Elasticsearch
from multiprocessing import Process, Pool 
from regions_list import regions
from secret import ElasticAccount, ElasticHost, ElasticPassword
from auth import listProfiles
es = Elasticsearch( # Cloud version
    cloud_id=f"{ElasticHost}",
    http_auth=(f"{ElasticAccount}", f"{ElasticPassword}"),
)
def main(params): 
    profile = params[0]
    region = params[1]
    resourceCounts = []
    try:
        resources_list_command = f"aws configservice get-discovered-resource-counts --profile {profile} --region {region} --output json"
        resources_output = subprocess.check_output(shlex.split(resources_list_command))
        jData = json.loads(resources_output)
        del jData['totalDiscoveredResources']
        resourceCounts = jData['resourceCounts']
    except Exception as e:
        # print(f"region: {region} is't been set")
        pass

    if len(resourceCounts) != 0:
        if resourceCounts[0]['resourceType'] == "AWS::Config::ResourceCompliance": del resourceCounts[0]
        for resource in resourceCounts:
            resource["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            resource["AccountName"] = profile
            resource['Region'] = region
            # print(resource)
            es.index(index='aws-config-resource',  body=resource)
starttime = time.time()
profiles = listProfiles()
paramlist = list(itertools.product(profiles, regions))
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, paramlist)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)