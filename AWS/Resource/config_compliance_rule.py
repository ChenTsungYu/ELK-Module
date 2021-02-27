"""
(終版)
configservice doc: describe-compliance-by-config-rule

https://docs.aws.amazon.com/cli/latest/reference/configservice/describe-compliance-by-config-rule.html
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
    jData = []
    try:
        resources_list_command = f"aws configservice describe-compliance-by-config-rule --compliance-types COMPLIANT NON_COMPLIANT --profile {profile} --region {region} --output json"
        resources_output = subprocess.check_output(shlex.split(resources_list_command))
        jData = json.loads(resources_output)
    except Exception as e:
        pass 
    if len(jData) != 0:
        # if len(jData['ComplianceByConfigRules']) == 0:  
        for compliance in jData['ComplianceByConfigRules']: 
            compliance["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            compliance["AccountName"] = profile
            compliance['Region'] = region
            # print(compliance)
            es.index(index='aws-config-compliance-rule',  body=compliance)
        
starttime = time.time()
profiles = listProfiles()
paramlist = list(itertools.product(profiles, regions))
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, paramlist)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)