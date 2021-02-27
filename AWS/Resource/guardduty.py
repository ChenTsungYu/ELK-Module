"""
AWS GuardDuty
docs:
https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings.html
https://docs.aws.amazon.com/cli/latest/reference/guardduty/get-findings.html
https://docs.aws.amazon.com/cli/latest/reference/guardduty/get-findings-statistics.html
https://docs.aws.amazon.com/cli/latest/reference/guardduty/list-detectors.html

===== 文件有查看每個 Severity 的區間值 =====
https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings.html
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
def ConvertSeverity(num):
    """
    Range of value: 
    High: 8.9 - 7.0
    Medium: 6.9 - 4.0
    Low: 3.9 - 1.0
    """
    severity = "High" if 7.0 <= num <= 8.9 else "Medium" if 4.0 <= num <= 6.9 else "Low" if 1.0 <= num <= 3.9 else "Undefined"
    category = "Critical" if severity == "High" else "Warning" if severity == "Medium" else "Normal" 
    return severity, category

def main(params): 
    profile = params[0]
    region = params[1]
    detectorIds = []
    try:
        detectors_list_command = f"aws guardduty list-detectors --profile {profile} --region {region} --output json"
        detectors_output = subprocess.check_output(shlex.split(detectors_list_command))
        detectors_data = json.loads(detectors_output)
        detectorIds = detectors_data['DetectorIds']
    except Exception as e:
        # print(f"error {e}")
        pass
    
    if len(detectorIds) != 0:
        for detectorId in detectorIds:
            findings_list_command = f"aws guardduty list-findings --detector-id {detectorId} --profile {profile} --region {region} --output json"
            findings_output = subprocess.check_output(shlex.split(findings_list_command))
            findings_data = json.loads(findings_output)
            for FindingId in findings_data['FindingIds']:
                resources_list_command = f"aws guardduty get-findings --detector-id  {detectorId} --finding-id {FindingId} --profile {profile} --region {region} --output json"
                resources_output = subprocess.check_output(shlex.split(resources_list_command))
                resources_data = json.loads(resources_output)
                for data in resources_data['Findings']:
                    cov_list = ConvertSeverity(data['Severity'])
                    data['Severity'] = cov_list[0]
                    data['Category'] = cov_list[1]
                    data["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                    data["AccountName"] = profile
                    data["Region"] = region
                    es.index(index='aws-resource-guardduty', body=data)
                    # print(data)

starttime = time.time()
profiles = listProfiles()
paramlist = list(itertools.product(profiles, regions))
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, paramlist)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)
