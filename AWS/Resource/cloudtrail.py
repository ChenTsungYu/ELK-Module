"""
docs:
https://docs.aws.amazon.com/cli/latest/reference/cloudtrail/lookup-events.html

AWS Console Login Record
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
    try:
        list_events_command = f"aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin --profile {profile} --region {region} --output json"
        events_output = subprocess.check_output(shlex.split(list_events_command))
        events_data = json.loads(events_output)
        for event in events_data['Events']:
            event = json.loads(event['CloudTrailEvent'])
            event["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            event["AccountName"] = profile
            event["Region"] = region
            es.index(index='aws-resource-cloudtrail', body=event)  
    except Exception as e:
        # print(f"error {e} ")
        pass

starttime = time.time()
profiles = listProfiles()
paramlist = list(itertools.product(profiles, regions))
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, paramlist)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)