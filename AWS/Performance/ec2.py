#coding=utf-8
"""
EC2 Performance(終版) => 平行處理

Docs: 查看 EC2 有的 Metrics
https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/viewing_metrics_with_cloudwatch.html
https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/list-metrics.html
https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/get-metric-statistics.html
https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/US_SingleMetricPerInstance.html
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
        metricDataQueriesList.append({'Id': f'esm{i}', 'MetricStat': {"Metric": metric, 'Period': 86400, 'Stat': 'Maximum'} } )
    return metricDataQueriesList

metricNameList = ['CPUUtilization', 'NetworkIn', 'NetworkOut']
dimensionsNameList = ['InstanceId']
def main(params): 
    profile = params[0]
    region = params[1]
    dataPoint = {}
    metricsDataList = []
    metricData = []
    credentials = getCredentials(profile)
    try:
        metrics_list_command = f"aws cloudwatch list-metrics --namespace AWS/EC2 --profile {profile} --region {region}  --output json"
        metrics_output = subprocess.check_output(shlex.split(metrics_list_command))
        metricsDataList = json.loads(metrics_output)
    except Exception as e:
        # print(f"region: {region} is't been set")
        print("metrics_list_command error: ", e)
        pass
    # print(profile, region)

    if len(metricsDataList) != 0 and len(metricsDataList['Metrics']) != 0:
        instanceResults = list(filter(lambda m: m['MetricName'] in metricNameList and len(m['Dimensions']) != 0 and m['Dimensions'][0]["Name"] in dimensionsNameList, metricsDataList['Metrics']))
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
            # 單一 Region 只有一台的情況下，labels 並不會回傳 EC2 Instance 的 ID
            # 撈取同一 MetricName 且包含不同統計(Statistics)類型情況下，如: 撈取 MetricName 為 CPUUtilization 的 Average 和 Maximum ，labels 的回傳結果會包含該 EC2 Instance 的 Statistics 類型
            if len(labels) == 2: 
                labels.insert(0, instanceResults[0]['Dimensions'][0]['Value'])

            for data in data_list:
                dataPoint['AccountName'] = profile
                dataPoint["Time"], dataPoint["Value"] = data[0], data[1]
                dataPoint['InstanceId'], dataPoint["Region"], dataPoint["Label"], dataPoint["Statistics"] = labels[0], region, labels[-2], labels[-1]
                dataPoint['Unit'] = "Percent" if labels[-2] == "CPUUtilization" else "Bytes"
                print("dataPoint: ", dataPoint)
                # es.index(index = 'aws-performance-ec2', body = dataPoint)
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
