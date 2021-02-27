#coding=utf-8
"""
Elasticsearch Performance(終版)
Docs:
https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/es-managedomains-cloudwatchmetrics.html
https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html
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

metricNameList = ['MasterReachableFromNode', 'ClusterIndexWritesBlocked', 'ClusterStatus.green', 'ClusterStatus.yellow', 'ClusterStatus.red', 'SearchableDocuments', 'DeletedDocuments', 'CPUUtilization', 'FreeStorageSpace', 'Nodes', 'AutomatedSnapshotFailure', 'KibanaHealthyNodes', 'JVMMemoryPressure', 'SysMemoryUtilization']
def main(params):
    profile = params[0]
    region = params[1]
    dataPoint = {}
    metricsDataList = []
    metricData = []
    credentials = getCredentials(profile)
    try:
        metrics_list_command = f"aws cloudwatch list-metrics --namespace AWS/ES --profile {profile} --region {region} --output json"
        metrics_output = subprocess.check_output(shlex.split(metrics_list_command))
        metricsDataList = json.loads(metrics_output)
    except Exception as e:
        pass
    if len(metricsDataList) != 0 and len(metricsDataList['Metrics']) != 0:
        clusterResults = list(filter(lambda m: m['MetricName'] in metricNameList and len(m['Dimensions']) != 0, metricsDataList['Metrics']))
        metricDataQueriesList = getMetricDataQueriesList(clusterResults, profile)
        try:
            metricData = getMetricData(metricDataQueriesList, region, credentials)
        except Exception as e:
            pass
        for metricResults in metricData:
            timestamps = metricResults['Timestamps']
            values = metricResults['Values']
            data_list = list(zip(timestamps, values))
            labels = metricResults['Label'].split(" ")
            # 單一Region 只有一台的情況下，labels 並不會回傳 ES Cluster的 ID
            if len(labels) == 1: labels.insert(0, clusterResults[0]['Dimensions'][0]['Value'])
            for data in data_list:
                dataPoint['AccountName'] = profile
                dataPoint['Region'] = region
                dataPoint["Time"], dataPoint["Value"] = data[0], data[1]
                dataPoint['InstanceId'], dataPoint["Label"], dataPoint["Statistics"] = labels[0], labels[-1], "Average"
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