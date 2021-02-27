#coding=utf-8
"""
Cloudfront Performance
Docs:
查看 Cloudfront 有的 Metrics
https://awscli.amazonaws.com/v2/documentation/api/latest/reference/cloudwatch/list-metrics.html
https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/programming-cloudwatch-metrics.html#cloudfront-metrics-global-values
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
metricNameList = ['Requests', 'TotalErrorRate', "BytesDownloaded"]
def getMetricDataQueriesList(metricData: list, profile: str) -> "建構 MetricDataQueries 所需之參數":
    metricDataQueriesList = []
    i = 0
    for metric in metricData:
        i += 1
        if metric['MetricName'] == "Requests" or metric['MetricName'] == "BytesDownloaded":
            metricDataQueriesList.append({'Id': f'esa{i}', 'MetricStat': {"Metric": metric, 'Period': 86400, 'Stat': 'Sum'}})
        else:
            metricDataQueriesList.append({'Id': f'esa{i}', 'MetricStat': {"Metric": metric, 'Period': 86400, 'Stat': 'Average'}})
    return metricDataQueriesList

def main(params): 
    profile = params
    region = "us-east-1"
    dataPoint = {}
    metricsDataList = []
    metricData = []
    credentials = getCredentials(profile)
    try:
        """
        cloudfront 屬於 Global， 故 region 必需為 us-east-1，才能取得 metrics data
        """
        metrics_list_command = f"aws cloudwatch list-metrics --namespace AWS/CloudFront --profile {profile} --region {region}  --output json"
        metrics_output = subprocess.check_output(shlex.split(metrics_list_command))
        metricsDataList = json.loads(metrics_output)
    except Exception as e:
        # print("metrics_list_command error: ", e)
        pass
    if len(metricsDataList) != 0 and len(metricsDataList['Metrics']) != 0:
        distributionResults = list(filter(lambda m: m['MetricName'] in metricNameList and len(m['Dimensions']) != 0, metricsDataList['Metrics']))
        metricDataQueriesList = getMetricDataQueriesList(distributionResults, profile)
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
            for data in data_list:
                dataPoint['AccountName'] = profile
                dataPoint["Time"], dataPoint["Value"] = data[0], data[1]
                dataPoint['DistributionId'], dataPoint["Region"], dataPoint["Label"] = labels[0], region, labels[1]
                dataPoint['Statistics'] = "Average" if labels[1] == "TotalErrorRate" else "Sum"
                # print("dataPoint: ", dataPoint)
                es.index(index = 'aws-performance-cloudfront', body = dataPoint)
starttime = time.time()
profiles = listProfiles()
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, profiles)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)
pool.close()