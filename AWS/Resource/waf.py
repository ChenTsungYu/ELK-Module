#coding=utf-8
"""
AWS WAF
doc:
https://docs.aws.amazon.com/cli/latest/reference/waf/index.html
https://docs.aws.amazon.com/cli/latest/reference/waf/get-rule.html
https://docs.aws.amazon.com/cli/latest/reference/waf/list-rules.html
https://docs.aws.amazon.com/cli/latest/reference/waf/list-rule-groups.html
https://docs.aws.amazon.com/cli/latest/reference/index.html#cli-aws
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

def getWafs(profile, region):
    wafs_list_command = f"aws waf list-rules --profile {profile} --region {region} --output json"
    wafs_output = subprocess.check_output(shlex.split(wafs_list_command))
    wafs_data = json.loads(wafs_output)
    return wafs_data

def main(params): 
    profile = params[0]
    region = params[1]
    wafs = []
    try:
        wafs = getWafs(profile, region)
    except Exception as e:
        pass

    print("wafs: ", wafs)
    # if len(wafs) != 0:


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