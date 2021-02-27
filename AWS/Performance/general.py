#coding=utf-8
import boto3
from datetime import datetime
def getMetricData(metricDataQueriesList: list, region: str, credentials) -> "取得 Metric 結果":
    if len(metricDataQueriesList) == 0: return metricDataQueriesList
    response = boto3.client('cloudwatch',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'],
        region_name=region
    ).get_metric_data(
        MetricDataQueries= metricDataQueriesList,
        StartTime=datetime(2021, 2, 1),
        EndTime=datetime(2021, 3, 1)
    )
    return response['MetricDataResults']