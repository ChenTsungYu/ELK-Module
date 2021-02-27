"""
AWS get-rightsizing-recommendation
docs:
https://awscli.amazonaws.com/v2/documentation/api/latest/reference/ce/get-rightsizing-recommendation.html
"""
import subprocess, json, shlex, pytz, time, simplejson
from datetime import datetime
from elasticsearch import Elasticsearch
from multiprocessing import Process, Pool 
from secret import ElasticAccount, ElasticHost, ElasticPassword
from auth import listProfiles
es = Elasticsearch( # Cloud version
    cloud_id=f"{ElasticHost}",
    http_auth=(f"{ElasticAccount}", f"{ElasticPassword}"),
)
def main(params): 
    profile = params
    try:
        resources_list_command = f"aws ce get-rightsizing-recommendation --configuration RecommendationTarget=CROSS_INSTANCE_FAMILY,BenefitsConsidered=true --service AmazonEC2 --profile {profile} --output json"
        resources_output = subprocess.check_output(shlex.split(resources_list_command))
    except Exception as e:
        pass
    dicts = json.loads(resources_output)
    timestamp = dicts['Metadata']['GenerationTimestamp']
    rightsizingRecommendations = dicts['RightsizingRecommendations']
    # print(dicts['Summary'])
    for v in rightsizingRecommendations:
        v["@timestamp"] = timestamp
        v["AccountName"] = profile
        # print(v)
        es.index(index='aws-ec2-rightsizing', body=v)

starttime = time.time()
profiles = listProfiles()
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, profiles)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)