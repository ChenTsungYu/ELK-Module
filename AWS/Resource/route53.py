"""
docs:
https://awscli.amazonaws.com/v2/documentation/api/latest/reference/route53/list-resource-record-sets.html
https://awscli.amazonaws.com/v2/documentation/api/latest/reference/route53/list-hosted-zones.html
https://awscli.amazonaws.com/v2/documentation/api/latest/reference/route53/index.html
Rount53:
Name 、Type、Value
"""
import subprocess, json, shlex, pytz, time, itertools
from datetime import datetime
from elasticsearch import Elasticsearch
from multiprocessing import Process, Pool 
from secret import ElasticAccount, ElasticHost, ElasticPassword
from auth import listProfiles
es = Elasticsearch( # Cloud version
    cloud_id=f"{ElasticHost}",
    http_auth=(f"{ElasticAccount}", f"{ElasticPassword}"),
)
def ListHostZones(profile):
    list_hosted_zones_command = f"aws route53 list-hosted-zones --profile {profile} --region us-east-1 --output json"
    list_hosted_zones_output = subprocess.check_output(shlex.split(list_hosted_zones_command))
    hosted_zones_data = json.loads(list_hosted_zones_output)
    return hosted_zones_data['HostedZones']

def main(params): 
    profile = params
    hosted_zones = ListHostZones(profile)
    for zone in hosted_zones:
        list_resource_record_command = f"aws route53 list-resource-record-sets --hosted-zone-id {zone['Id']} --profile {profile} --region us-east-1 --output json"
        list_resource_record_output = subprocess.check_output(shlex.split(list_resource_record_command))
        resource_record_data = json.loads(list_resource_record_output)
        for record in resource_record_data['ResourceRecordSets']:
            record['DomainName'] = zone['Name']
            try:
                if record["AliasTarget"]: record["ResourceRecords"] = [{'Value': f'ALIAS {record["AliasTarget"]["DNSName"]}'}]
            except Exception as e:
                # AliasTarget 只有在'Type': 'A' 才會出現，其餘皆不會有
                pass
            res = [records["Value"] for records in record['ResourceRecords']]
            record['ResourceRecords'] = 'None' if res == [] else ", ".join(res)
            record["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            record["AccountName"] = profile
            es.index(index='aws-resource-route53', body=record)

starttime = time.time()
profiles = listProfiles()
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, profiles)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)