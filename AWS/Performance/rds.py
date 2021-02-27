
#coding=utf-8
"""
(終版)
Docs: 查看 RDS 有的 Metrics
https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MonitoringOverview.html
https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/viewing_metrics_with_cloudwatch.html
https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/list-metrics.html
https://aws.amazon.com/tw/premiumsupport/knowledge-center/cloudwatch-getmetricdata-api/
https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html

資料結構請見 template
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

def getMetricDataQueriesList(metricData, profile) -> "建構 MetricDataQueries 所需之參數":
    metricDataQueriesList = []
    i = 0
    for metric in metricData:
        i += 1
        metricDataQueriesList.append({'Id': f'rds{i}', 'MetricStat': {"Metric": metric, 'Period': 86400, 'Stat': 'Average'}})
    return metricDataQueriesList

metricNameList = ['CPUUtilization', 'FreeStorageSpace', 'FreeableMemory', 'FreeLocalStorage', 'DatabaseConnections']
dimensionsNameList = ['DBInstanceIdentifier', 'DBClusterIdentifier']
def main(params):
    profile = params[0]
    region = params[1]
    dataPoint = {}
    metricsDataList = []
    metricData = []
    credentials = getCredentials(profile)
    try:
        metrics_list_command = f"aws cloudwatch list-metrics --namespace AWS/RDS --profile {profile} --region {region} --output json"
        metrics_output = subprocess.check_output(shlex.split(metrics_list_command))
        metricsDataList = json.loads(metrics_output)
    except Exception as e:
        print("metrics_list_command error: ", e)
    if len(metricsDataList) != 0 and len(metricsDataList['Metrics']) != 0:
        instanceResults = list(filter(lambda m: m['MetricName'] in metricNameList and len(m['Dimensions']) != 0 and m['Dimensions'][0]["Name"] in dimensionsNameList, metricsDataList['Metrics']))
        metricDataQueriesList = getMetricDataQueriesList(instanceResults, profile)
        try:
            metricData = getMetricData(metricDataQueriesList, region, credentials)
        except Exception as e:
            print("getMetricData error: ", e)
        # print(profile, region)
        for metricResults in metricData:
            labels = metricResults['Label'].split(" ")
            # 單一Region 只有一台的情況下，labels 並不會回傳 DB Instance 的 ID
            if len(labels) == 1: labels.insert(0, instanceResults[0]['Dimensions'][0]['Value'])

            timestamps = metricResults['Timestamps']
            values = metricResults['Values']
            data_list = list(zip(timestamps, values))
            for data in data_list:
                dataPoint['AccountName'] = profile
                dataPoint["Time"], dataPoint["Value"] = data[0], data[1]
                dataPoint['InstanceId'], dataPoint["Region"], dataPoint["Label"], dataPoint["Statistics"] = labels[0], region, labels[-1], "Average"
                # print("dataPoint: ", dataPoint)
                # es.index(index = 'aws-performance-rds', body = dataPoint)

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