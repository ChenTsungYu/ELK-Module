#coding=utf-8
"""

doc:
https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-vpcs.html
https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-network-acls.html
https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-route-tables.html
https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-security-groups.html
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

def getVpcIds(profile, region):
    vpcs_list_command = f"aws ec2 describe-vpcs --profile {profile} --region {region} --output json"
    vpcs_output = subprocess.check_output(shlex.split(vpcs_list_command))
    vpcs_data = json.loads(vpcs_output)
    return vpcs_data['Vpcs']
    
def getNetworkAcls(profile, vpcIds, region):
    network_acls_list_command = f"aws ec2 describe-network-acls --filters Name=vpc-id,Values={vpcIds} --profile {profile} --region {region} --output json"
    network_acls_output = subprocess.check_output(shlex.split(network_acls_list_command))
    network_acls_data = json.loads(network_acls_output)
    network_acls_data['NetworkAcls']
    return network_acls_data['NetworkAcls']
    
def getRouteTables(profile, vpcIds, region):
    routeTables_list_command = f"aws ec2 describe-route-tables --filters Name=vpc-id,Values={vpcIds} --profile {profile} --region {region} --output json"
    routeTables_output = subprocess.check_output(shlex.split(routeTables_list_command))
    routeTables_data = json.loads(routeTables_output)
    return routeTables_data['RouteTables']

def getSecurityGroups(profile, vpcIds, region):
    securityGroups_list_command = f"aws ec2 describe-security-groups --filters Name=vpc-id,Values={vpcIds} --profile {profile} --region {region} --output json"
    securityGroups_output = subprocess.check_output(shlex.split(securityGroups_list_command))
    securityGroups_data = json.loads(securityGroups_output)
    return securityGroups_data['SecurityGroups']

def main(params): 
    profile = params[0]
    region = params[1]
    vpcs = []
    try:
        vpcs = getVpcIds(profile, region)
    except Exception as e:
        pass
    print("vpcs: ", vpcs)
    if len(vpcs) != 0:
        vpcIds_list = []
        cidrs_list = [] 
        for vpcid in vpcs:
            vpcIds_list.append(vpcid['VpcId'])
            cidrs_list.append(vpcid['CidrBlock'])

        vpcIds = ",".join(vpcIds_list)
        cidrs = ",".join(cidrs_list)

        print("vpcIds: ", vpcIds)
        print("cidrs: ", cidrs)
        print("-------")
        networkAcls = getNetworkAcls(profile, vpcIds, region)
        print("networkAcls: ", networkAcls)
        print("-------")
        routeTables = getRouteTables(profile, vpcIds, region)
        print("RouteTables: ", routeTables)
        print("-------")
        securityGroups = getSecurityGroups(profile, vpcIds, region)
        print("securityGroups: ", securityGroups)
        print("=======")

starttime = time.time()
profiles = listProfiles()
paramlist = list(itertools.product(profiles, regions))
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main,paramlist)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)