#coding=utf-8
"""
(終版)
doc:
https://docs.aws.amazon.com/cli/latest/reference/acm/describe-certificate.html
https://docs.aws.amazon.com/cli/latest/reference/acm/list-certificates.html
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
def listCertificate(profile, region):
    lis_certificate_command = f"aws acm list-certificates --profile {profile} --region {region} --output json"
    lis_certificate_output = subprocess.check_output(shlex.split(lis_certificate_command))
    lis_certificate_data = json.loads(lis_certificate_output)
    return lis_certificate_data['CertificateSummaryList']

def getAcms(profile, region, arn):
    acms_list_command = f"aws acm describe-certificate --certificate-arn {arn} --profile {profile} --region {region} --output json"
    acms_output = subprocess.check_output(shlex.split(acms_list_command))
    acms_data = json.loads(acms_output)
    return acms_data['Certificate']
    
def main(params): 
    profile = params[0]
    region = params[1]
    acms = []
    try:
        acms = listCertificate(profile, region)
    except Exception as e:
        pass
    if len(acms) != 0:
        for acm in acms: 
            arns = getAcms(profile, region, acm['CertificateArn'])
            arns["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            arns["AccountName"] = profile
            arns["Region"] = region
            arns['InUse'] = "Yes" if len(arns['InUseBy']) > 0 else "No"
            arns["AdditionalNames"] = arns['SubjectAlternativeNames'][-1]
            es.index(index='aws-resource-acm', body=arns)

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