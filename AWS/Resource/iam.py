"""
IAM清單
docs:
https://docs.aws.amazon.com/cli/latest/reference/iam/index.html
https://docs.aws.amazon.com/cli/latest/reference/iam/get-user-policy.html
https://docs.aws.amazon.com/cli/latest/reference/iam/list-attached-user-policies.html
https://docs.aws.amazon.com/cli/latest/reference/iam/list-users.html

Steps:
list users -> list-attached-user-policies
"""
import subprocess, json, shlex, pytz, time, itertools, csv, io, base64, re
from datetime import datetime, date
from elasticsearch import Elasticsearch
from multiprocessing import Process, Pool
from auth import listProfiles
from secret import ElasticAccount, ElasticHost, ElasticPassword
es = Elasticsearch( # Cloud version
    cloud_id=f"{ElasticHost}",
    http_auth=(f"{ElasticAccount}", f"{ElasticPassword}"),
)
def CountKeyAge(lastRotated, isActive, creationTime) -> "計算key存在的天數":
    if isActive == "false": return "None"
    if lastRotated != "N/A":
        # 非 N/A 表有換過 key，Console 上的Key age 會採用最新一次 rotate 的時間做計算
        creationTime = lastRotated.replace('+00:00','Z')
    else:
        creationTime = creationTime.replace('+00:00','Z')
    now_time = datetime.strptime(creationTime, "%Y-%m-%dT%H:%M:%SZ")
    d0 = now_time.date()
    d1 = date.today()
    days = "Today" if (d1 - d0).days < 1 else "Yesterday" if (d1 - d0).days == 1 else f'{(d1 - d0).days} days'
    """
    if (d1 - d0).days == 0:
        days = "Today"
    elif (d1 - d0).days == 1:
        days = "Yesterday"
    else:
        days = f'{(d1 - d0).days} days'
    """
    return days

def CountPasswordAge(isEnable, lastChanged, creationTime) -> "計算密碼存在的天數":
    if isEnable == "false": return "None"
    if lastChanged != "N/A":
        creationTime = lastChanged.replace('+00:00','Z')

    now_time = datetime.strptime(creationTime, "%Y-%m-%dT%H:%M:%SZ")
    d0 = now_time.date()
    d1 = date.today()
    
    days = "Today" if (d1 - d0).days < 1 else "Yesterday" if (d1 - d0).days == 1 else f'{(d1 - d0).days} days'
    return days

def CountLastActive(passwordLastUsed, keyLastUsed) -> "計算距離上次登入的天數":
    """
    Possible combination:
    passwordLastUsed     keyLastUsed
    ---------------- | ---------------- 
        N/A               N/A {1}
     no_information       N/A {1}
     
     DateTime             N/A {2}
     no_information     DateTime {3}
        N/A             DateTime {3}
        
     DateTime           DateTime {4}
    """
    
    if (passwordLastUsed == "N/A" or passwordLastUsed == "no_information") and keyLastUsed == "N/A" : return "None" # {1}

    if passwordLastUsed != "N/A" and passwordLastUsed != "no_information" and keyLastUsed == "N/A": # {2}
        creationTime = passwordLastUsed.replace('+00:00','Z')
        
    elif keyLastUsed != "N/A" and (passwordLastUsed == "N/A" or passwordLastUsed == "no_information"): # {3}
        creationTime = keyLastUsed.replace('+00:00','Z')
        
    else:
        creationTime = keyLastUsed.replace('+00:00','Z') if keyLastUsed > passwordLastUsed else passwordLastUsed.replace('+00:00','Z') # {4}
        
    now_time = datetime.strptime(creationTime, "%Y-%m-%dT%H:%M:%SZ")
    d0 = now_time.date()
    d1 = date.today()
    days = "Today" if (d1 - d0).days < 1 else "Yesterday" if (d1 - d0).days == 1 else f'{(d1 - d0).days} days'
    return days

def ConvertBase64(profile):
    list_report_command = f"aws iam get-credential-report --profile {profile} --region us-east-1 --output json"
    report_output = subprocess.check_output(shlex.split(list_report_command))
    report_data = json.loads(report_output)

    data = base64.b64decode(report_data['Content'])
    my_json = data.decode('utf8').replace("'", '"')

    reader = csv.DictReader(io.StringIO(my_json))
    json_data = json.dumps(list(reader))

    json_data = json.loads(json_data)
    if json_data[0]["user"] == "<root_account>": del json_data[0]
    return json_data

def listUsers(profile):
    list_users_command = f"aws iam get-account-authorization-details --profile {profile} --region us-east-1 --filter User --output json"
    users_output = subprocess.check_output(shlex.split(list_users_command))
    users_data = json.loads(users_output)
    return users_data

def main(profile): 
    users_data = listUsers(profile)
    base64_data = ConvertBase64(profile)
    for user in users_data["UserDetailList"]:
        user['CreateDate'] = user['CreateDate']
        res_Policy = [ policy['PolicyName'] for policy in user['AttachedManagedPolicies'] ]
        user['AttachedPolicies'] = 'None' if res_Policy == [] else ", ".join(res_Policy)
        res_group = [ group for group in user['GroupList'] ]
        user['Groups'] = 'None' if res_group == [] else ", ".join(res_group)

        for base_user in base64_data:
            if base_user['user'] == user['UserName']:
                creation_time, is_active, last_rotated = base_user['user_creation_time'], base_user['access_key_1_active'], base_user['access_key_1_last_rotated']
                
                user["@timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                user['AccountName'] = profile
                user['key_age'] = CountKeyAge(last_rotated, is_active ,creation_time)
                user['password_age'] = CountPasswordAge(base_user['password_enabled'], base_user['password_last_changed'], creation_time)
                user['last_activity'] = CountLastActive(base_user['password_last_used'], base_user['access_key_1_last_used_date'])
                user["MFA"] = "Not Enalbe" if base_user['mfa_active'] == "false" else "Enalbe"
                print("user: ", user)
                # es.index(index='aws-resource-iam', body=user)
    
starttime = time.time()
profiles = listProfiles()
#Generate processes equal to the number of cores
pool = Pool()
#Distribute the parameter sets evenly across the cores
pool.map(main, profiles)
output = 'It took {} seconds with multiprocessing'.format(time.time() - starttime)
print(output)