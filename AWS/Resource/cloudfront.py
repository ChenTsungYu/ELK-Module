"""
(終版)
docs:
https://docs.aws.amazon.com/cli/latest/reference/cloudfront/list-distributions.html
https://docs.aws.amazon.com/cli/latest/reference/cloudfront/index.html#cli-aws-cloudfront

CloudFront:
ID、CNAME、CloudFront Domain、CDN Origin Server
"""
import subprocess, json, shlex, pytz, time, itertools
from datetime import datetime
from elasticsearch import Elasticsearch
from multiprocessing import Process, Pool 
from secret import ElasticAccount, ElasticHost, ElasticPassword
from auth import listProfiles
from general import ConvertToLocalTime
es = Elasticsearch( # Cloud version
    cloud_id=f"{ElasticHost}",
    http_auth=(f"{ElasticAccount}", f"{ElasticPassword}"),
)

def ListDistributions(profile):
    list_distributions_command = f"aws cloudfront list-distributions --profile {profile} --region us-east-1 --output json"
    distributions_output = subprocess.check_output(shlex.split(list_distributions_command))
    distributions_data = json.loads(distributions_output)
    return distributions_data['DistributionList']['Items']

def main(params): 
    profile = params
    distributions_data = ListDistributions(profile)
    for item in distributions_data:
        """  ------ Origins ------  """
        origins_list = [ origins for origins in item['Origins']["Items"] ]
        origins = [origins["DomainName"] for origins in origins_list]
        item['CDNOrigin'] = 'None' if origins == [] else ", ".join(origins)
        """ ------ Aliases(CNAME) ------  """
        if item['Aliases']['Quantity'] == 0: item['Aliases']['Items'] = []
        aliases_list = [ aliases for aliases in item['Aliases']["Items"] ]
        item['CNAME'] = 'None' if aliases_list == [] else ", ".join(aliases_list)
        item["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        item["AccountName"] = profile
        # print("item: ", item)
        es.index(index='aws-resource-cloudfront', body=item)

starttime = time.time()
profiles = listProfiles()
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, profiles)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)