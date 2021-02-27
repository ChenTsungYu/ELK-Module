#coding=utf-8
"""
EC2 Performance - CW Agent(終版)
docs:
https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/metrics-collected-by-CloudWatch-agent.html
https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/viewing_metrics_with_cloudwatch.html
https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html
"""
import subprocess, json, shlex, pytz, time, itertools
from datetime import datetime
from elasticsearch import Elasticsearch
from multiprocessing import Process, Pool 
from regions_list import regions
from secret import ElasticAccount, ElasticHost, ElasticPassword
from auth import getCredentials, listProfiles
from general import getMetricData
es = Elasticsearch( # Cloud version
    cloud_id=f"{ElasticHost}",
    http_auth=(f"{ElasticAccount}", f"{ElasticPassword}"),
)
def getMetricDataQueriesList(metricData: list, profile: str) -> "建構 MetricDataQueries 所需之參數":
    metricDataQueriesList = []
    i = 0
    for metric in metricData:
        i += 1
        metricDataQueriesList.append({'Id': f'esa{i}', 'MetricStat': {"Metric": metric, 'Period': 86400, 'Stat': 'Average'}})
    return metricDataQueriesList
"""
注意：CW Agent 預設的 Metric Name 會因作業系統不同而有所差異，下方的 metricNameList 採 Linux 系統預設的 Metric Name
"""  
metricNameList = ['mem_used_percent', 'disk_used_percent']
dimensionsNameList = ['InstanceId']
def main(params): 
    profile = params[0]
    region = params[1]
    dataPoint = {}
    metricsDataList = []
    metricData = []
    credentials = getCredentials(profile)
    try:
        metrics_list_command = f"aws cloudwatch list-metrics --namespace CWAgent --profile {profile} --region {region}  --output json"
        metrics_output = subprocess.check_output(shlex.split(metrics_list_command))
        metricsDataList = json.loads(metrics_output)
    except Exception as e:
        # print("metrics_list_command error: ", e)
        pass
    # print(profile, region)
    if len(metricsDataList) != 0 and len(metricsDataList['Metrics']) != 0:
        instanceResults = list(filter(lambda m: m['MetricName'] in metricNameList and len(m['Dimensions']) != 0 , metricsDataList['Metrics']))
        metricDataQueriesList = getMetricDataQueriesList(instanceResults, profile)
        try:
            metricData = getMetricData(metricDataQueriesList, region, credentials)
        except Exception as e:
            # print("getMetricData error: ", e)
            pass
        for metricResults in metricData:
            labels = metricResults['Label'].split(" ")
            timestamps = metricResults['Timestamps']
            values = metricResults['Values']
            data_list = list(zip(timestamps, values))
            # 單一 Region 只有一台的情況下，labels 並不會回傳 EC2 Instance 的 ID; Statistics 只有指定一種的情況下，labels 並不會回傳 Statistics 類型，要兩種以上才有
            if labels[-1] == "disk_used_percent":
                if labels[-2] != "/": continue # path 不為 "/" 時，略過不寫入index 
                labels[0:3] = [] # ['nvme0n1p1', 'ext4', '/', 'disk_used_percent'] => ['disk_used_percent']
                labels.insert(0, instanceResults[0]['Dimensions'][1]['Value'])

            if len(labels) == 1 and labels[-1] == "mem_used_percent":
                labels.insert(0, instanceResults[0]['Dimensions'][1]['Value'])

            for data in data_list:
                dataPoint['AccountName'] = profile
                dataPoint["Time"], dataPoint["Value"] = data[0], data[1]
                dataPoint['InstanceId'], dataPoint["Region"], dataPoint["Label"], dataPoint["Statistics"] = labels[0], region, labels[1], "Average"
                dataPoint['Unit'] = "Percent"
                # print("dataPoint: ", dataPoint)
                es.index(index = 'aws-performance-ec2-cwagent', body = dataPoint)
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