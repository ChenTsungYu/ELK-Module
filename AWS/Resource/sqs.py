#coding=utf-8
"""
(終版)
doc:
https://docs.aws.amazon.com/cli/latest/reference/sqs/list-queues.html
"""
import subprocess, json, shlex, pytz, time, itertools
from datetime import datetime
from elasticsearch import Elasticsearch
from multiprocessing import Process, Pool 
from regions_list import regions
from secret import ElasticAccount, ElasticHost, ElasticPassword
from auth import getCredentials, listProfiles
es = Elasticsearch( # Cloud version
    cloud_id=f"{ElasticHost}",
    http_auth=(f"{ElasticAccount}", f"{ElasticPassword}"),
)
def listSqs(profile, region):
    lis_sqs_command = f"aws sqs list-queues --profile {profile} --region {region} --output json"
    lis_sqs_output = subprocess.check_output(shlex.split(lis_sqs_command))
    lis_sqs_data = json.loads(lis_sqs_output)
    return lis_sqs_data['QueueUrls']

def main(params): 
    profile = params[0]
    region = params[1]
    sqs = []
    sqsObj = {}
    try:
        sqs = listSqs(profile, region)
    except Exception as e:
        pass
    if len(sqs) != 0:
        sqsUrl = sqs[0]
        sqsName = (sqsUrl.split('/'))[-1]
        sqsUrl = sqsUrl.replace('queue.',"").replace('//',"//sqs.")
        sqsObj["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        sqsObj["AccountName"] = profile
        sqsObj['Region'], sqsObj['SqsUrl'], sqsObj['SqsName'] = region, sqsUrl, sqsName
        # print("sqsObj: ", sqsObj)
        es.index(index = 'aws-resource-sqs', body = sqsObj)
    
starttime = time.time()
profiles = listProfiles()
paramlist = list(itertools.product(profiles, regions))
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main,paramlist)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)
pool.close()