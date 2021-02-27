#coding=utf-8
import subprocess, shlex, pytz, time, boto3
def listProfiles() -> "取得所有 Config 底下的所有 profile":
    """
    * return a list
    * profiles_output 為 Data type 為 <class 'bytes'> 需 decode
    """
    profiles_list_command = f"aws configure list-profiles"
    profiles_output = subprocess.check_output(shlex.split(profiles_list_command))
    accountList = profiles_output.decode().split()
    accountList = list(filter(lambda profile: profile != "MS" and profile != "default", accountList))
    return accountList

def getCredentials(profile):
    arn_list_command = f"aws configure get role_arn --profile {profile} "
    arn_output = subprocess.check_output(shlex.split(arn_list_command))
    arn = arn_output.decode().strip()
    sts_client = boto3.client('sts')
    assumed_role_object = sts_client.assume_role(
        RoleArn=arn,
        RoleSessionName="AssumeRoleSession1",
        DurationSeconds=3000
    )
    credentials = assumed_role_object['Credentials']
    return credentials


if __name__ == "__main__":
    pass